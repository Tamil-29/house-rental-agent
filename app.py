"""
==============================================================================
Project Name: House Rental Agent
Technology: Python Flask, MySQL (PyMySQL), HTML5, CSS3, JavaScript, Bootstrap 5
Description: Simple, robust, college-level House Rental Management System.
             Allows house owners to list houses and manage rental requests,
             tenants to search houses and submit rental requests, and an
             administrator to manage users, listings, and audit requests.
==============================================================================
"""

import os
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, jsonify
)
import pymysql
import pymysql.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from agentic_ai import ReActRentalAgent, RentalAgentTools

# ----------------------------------------------------------------------------
# Application Initialization & Configuration
# ----------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'house_rental_college_secret_key_2026')

# File Upload Settings
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Database Configuration (Configurable via environment variables)
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'root')
DB_NAME = os.environ.get('DB_NAME', 'house_rental_db')
DB_PORT = int(os.environ.get('DB_PORT', 3306))


# ----------------------------------------------------------------------------
# Database Helpers
# ----------------------------------------------------------------------------
def get_db_connection():
    """
    Establish and return a PyMySQL database connection with DictCursor.
    """
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


# Initialize Agentic AI Engine and Tool Suite
ai_agent = ReActRentalAgent(get_db_connection)
ai_tools = RentalAgentTools(get_db_connection)


def allowed_file(filename):
    """
    Check if uploaded file has an allowed image extension.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def init_db():
    """
    Bootstrap the database and execute database.sql if database or tables do not exist.
    """
    try:
        # Connect to MySQL server without selecting database first
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            autocommit=True
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};")
        conn.close()

        # Connect to the database and check if tables exist
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'users';")
            result = cursor.fetchone()
            if not result:
                sql_file_path = os.path.join(BASE_DIR, 'database.sql')
                if os.path.exists(sql_file_path):
                    with open(sql_file_path, 'r', encoding='utf-8') as f:
                        sql_commands = f.read().split(';')
                        for cmd in sql_commands:
                            cmd = cmd.strip()
                            if cmd:
                                cursor.execute(cmd)
                    print("[INFO] Database initialized successfully from database.sql.")
        conn.close()
    except Exception as e:
        print(f"[WARNING] Database initialization check: {e}")


# ----------------------------------------------------------------------------
# Authentication & Authorization Decorators
# ----------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in first to access this page.', 'warning')
                return redirect(url_for('login'))
            if session.get('role') not in allowed_roles:
                flash('Access denied: You do not have permission for this action.', 'danger')
                # Redirect user to their appropriate dashboard
                role = session.get('role')
                if role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif role == 'owner':
                    return redirect(url_for('owner_dashboard'))
                elif role == 'tenant':
                    return redirect(url_for('tenant_dashboard'))
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ----------------------------------------------------------------------------
# 1. HOME & PUBLIC BROWSING ROUTES
# ----------------------------------------------------------------------------
@app.route('/')
def index():
    """
    Home page: Display hero section, search form, and a few available houses.
    """
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM houses 
            WHERE status = 'Available' AND approved = 1 
            ORDER BY created_at DESC 
            LIMIT 6
        """)
        featured_houses = cursor.fetchall()
    conn.close()
    return render_template('index.html', featured_houses=featured_houses)


@app.route('/houses')
def houses():
    """
    Public houses catalog with search and multi-filtering:
    - location / keyword
    - maximum rent
    - number of bedrooms
    """
    location = request.args.get('location', '').strip()
    max_rent = request.args.get('max_rent', '').strip()
    bedrooms = request.args.get('bedrooms', '').strip()

    query = """
        SELECT * FROM houses 
        WHERE approved = 1
    """
    params = []

    if location:
        query += " AND (location LIKE %s OR title LIKE %s OR address LIKE %s)"
        like_loc = f"%{location}%"
        params.extend([like_loc, like_loc, like_loc])

    if max_rent:
        try:
            query += " AND rent <= %s"
            params.append(float(max_rent))
        except ValueError:
            pass

    if bedrooms:
        try:
            query += " AND bedrooms = %s"
            params.append(int(bedrooms))
        except ValueError:
            pass

    query += " ORDER BY status ASC, created_at DESC"

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(query, tuple(params))
        all_houses = cursor.fetchall()
    conn.close()

    return render_template('houses.html', houses=all_houses)


@app.route('/houses/<int:house_id>')
def house_details(house_id):
    """
    Detailed view of a single house listing including specifications,
    owner contact details, and the rental request trigger.
    """
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT h.*, u.name AS owner_name, u.phone AS owner_phone, u.email AS owner_email
            FROM houses h
            JOIN users u ON h.owner_id = u.id
            WHERE h.id = %s
        """, (house_id,))
        house = cursor.fetchone()

        if not house:
            conn.close()
            flash('The requested house listing does not exist.', 'danger')
            return redirect(url_for('houses'))

        # Check if the currently logged in tenant already requested this house
        user_request = None
        if session.get('role') == 'tenant':
            cursor.execute("""
                SELECT * FROM rental_requests 
                WHERE house_id = %s AND tenant_id = %s
            """, (house_id, session.get('user_id')))
            user_request = cursor.fetchone()

    conn.close()
    return render_template('house_details.html', house=house, user_request=user_request)


# ----------------------------------------------------------------------------
# 2. AUTHENTICATION ROUTES (REGISTER, LOGIN, LOGOUT)
# ----------------------------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration for Owners and Tenants.
    Validates name, unique email, phone, password, and role.
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', '').strip().lower()

        # Validation
        if not name or not email or not phone or not password or not role:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if role not in ['owner', 'tenant']:
            flash('Invalid role selected. Must be Owner or Tenant.', 'danger')
            return render_template('register.html')

        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Check if email is already registered
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                conn.close()
                flash('An account with this email already exists. Please login.', 'warning')
                return redirect(url_for('login'))

            # Hash the password securely using werkzeug
            hashed_password = generate_password_hash(password)

            cursor.execute("""
                INSERT INTO users (name, email, phone, password, role)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, email, phone, hashed_password, role))

        conn.close()
        flash('Registration successful! You can now log in with your credentials.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Role-based login for Admin, Owner, and Tenant.
    Stores user info in session and redirects to role dashboard.
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        selected_role = request.form.get('role', '').strip().lower()

        if not email or not password or not selected_role:
            flash('Please enter email, password, and select your role.', 'danger')
            return render_template('login.html')

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(user['password'], password):
            # Verify that the role matches
            if user['role'] != selected_role:
                flash(f'Account exists, but its registered role is "{user["role"]}", not "{selected_role}".', 'warning')
                return render_template('login.html')

            # Populate session
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']

            flash(f'Welcome back, {user["name"]}!', 'success')

            # Role-based dashboard redirect
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'owner':
                return redirect(url_for('owner_dashboard'))
            elif user['role'] == 'tenant':
                return redirect(url_for('tenant_dashboard'))
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    Clear session and redirect to login page.
    """
    session.clear()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('login'))


# ----------------------------------------------------------------------------
# 3. TENANT MODULE ROUTES
# ----------------------------------------------------------------------------
@app.route('/tenant/dashboard')
@login_required
@role_required(['tenant'])
def tenant_dashboard():
    """
    Tenant Dashboard: Displays tenant's rental requests and current statuses.
    """
    tenant_id = session.get('user_id')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT r.*, h.title AS house_title, h.location, h.rent, h.deposit, 
                   h.bedrooms, h.furnishing, h.image AS house_image,
                   u.name AS owner_name, u.phone AS owner_phone
            FROM rental_requests r
            JOIN houses h ON r.house_id = h.id
            JOIN users u ON h.owner_id = u.id
            WHERE r.tenant_id = %s
            ORDER BY r.request_date DESC
        """, (tenant_id,))
        requests_list = cursor.fetchall()

    conn.close()

    # Calculate statistics
    total = len(requests_list)
    pending = sum(1 for r in requests_list if r['status'] == 'Pending')
    accepted = sum(1 for r in requests_list if r['status'] == 'Accepted')

    stats = {
        'total_requests': total,
        'pending_requests': pending,
        'accepted_requests': accepted
    }

    return render_template('tenant_dashboard.html', requests=requests_list, stats=stats)


@app.route('/request-house/<int:house_id>', methods=['POST'])
@login_required
@role_required(['tenant'])
def request_house(house_id):
    """
    Submit a new rental request for a house.
    Status starts as 'Pending'.
    """
    tenant_id = session.get('user_id')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Check house availability
        cursor.execute("SELECT * FROM houses WHERE id = %s", (house_id,))
        house = cursor.fetchone()

        if not house:
            conn.close()
            flash('House listing not found.', 'danger')
            return redirect(url_for('houses'))

        if house['status'] == 'Rented':
            conn.close()
            flash('This house is already rented out.', 'warning')
            return redirect(url_for('house_details', house_id=house_id))

        # Check if tenant already requested this house
        cursor.execute("""
            SELECT id, status FROM rental_requests 
            WHERE house_id = %s AND tenant_id = %s
        """, (house_id, tenant_id))
        existing_req = cursor.fetchone()

        if existing_req:
            conn.close()
            flash(f'You have already sent a rental request for this house (Status: {existing_req["status"]}).', 'info')
            return redirect(url_for('tenant_dashboard'))

        # Insert new rental request
        cursor.execute("""
            INSERT INTO rental_requests (house_id, tenant_id, status)
            VALUES (%s, %s, 'Pending')
        """, (house_id, tenant_id))

    conn.close()
    flash('Rental request submitted successfully! The house owner will review it.', 'success')
    return redirect(url_for('tenant_dashboard'))


@app.route('/tenant/cancel-request/<int:request_id>', methods=['POST'])
@login_required
@role_required(['tenant'])
def tenant_cancel_request(request_id):
    """
    Allows a tenant to cancel their pending rental request.
    """
    tenant_id = session.get('user_id')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            DELETE FROM rental_requests 
            WHERE id = %s AND tenant_id = %s AND status = 'Pending'
        """, (request_id, tenant_id))

    conn.close()
    flash('Rental request cancelled.', 'info')
    return redirect(url_for('tenant_dashboard'))


# ----------------------------------------------------------------------------
# 4. OWNER MODULE ROUTES (CRUD HOUSES, ACCEPT/REJECT REQUESTS)
# ----------------------------------------------------------------------------
@app.route('/owner/dashboard')
@login_required
@role_required(['owner'])
def owner_dashboard():
    """
    Owner Dashboard: Lists all houses belonging to the logged-in owner,
    with direct edit/delete/status toggles and metric counters.
    """
    owner_id = session.get('user_id')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM houses 
            WHERE owner_id = %s 
            ORDER BY created_at DESC
        """, (owner_id,))
        owner_houses = cursor.fetchall()

        # Count pending rental requests for this owner's properties
        cursor.execute("""
            SELECT COUNT(*) AS pending_count 
            FROM rental_requests r
            JOIN houses h ON r.house_id = h.id
            WHERE h.owner_id = %s AND r.status = 'Pending'
        """, (owner_id,))
        pending_result = cursor.fetchone()
        pending_requests = pending_result['pending_count'] if pending_result else 0

    conn.close()

    total_houses = len(owner_houses)
    available_houses = sum(1 for h in owner_houses if h['status'] == 'Available')
    rented_houses = sum(1 for h in owner_houses if h['status'] == 'Rented')

    stats = {
        'total_houses': total_houses,
        'available_houses': available_houses,
        'rented_houses': rented_houses,
        'pending_requests': pending_requests
    }

    return render_template('owner_dashboard.html', houses=owner_houses, stats=stats)


@app.route('/owner/add-house', methods=['GET', 'POST'])
@login_required
@role_required(['owner'])
def add_house():
    """
    Add a new house listing with image upload support.
    """
    if request.method == 'POST':
        owner_id = session.get('user_id')
        title = request.form.get('title', '').strip()
        location = request.form.get('location', '').strip()
        address = request.form.get('address', '').strip()
        rent = request.form.get('rent', '').strip()
        deposit = request.form.get('deposit', '').strip()
        bedrooms = request.form.get('bedrooms', '').strip()
        bathrooms = request.form.get('bathrooms', '').strip()
        furnishing = request.form.get('furnishing', 'Furnished')
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'Available')

        # Form validations
        if not title or not location or not address or not rent or not deposit:
            flash('Please fill in all mandatory fields.', 'danger')
            return render_template('add_house.html')

        try:
            rent_val = float(rent)
            deposit_val = float(deposit)
            bedrooms_val = int(bedrooms)
            bathrooms_val = int(bathrooms)
        except ValueError:
            flash('Rent, deposit, bedrooms, and bathrooms must be valid numbers.', 'danger')
            return render_template('add_house.html')

        # Handle image upload
        image_filename = 'default_house.jpg'
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                sec_filename = secure_filename(file.filename)
                # Create unique name with timestamp
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                image_filename = f"house_{owner_id}_{timestamp}_{sec_filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO houses (
                    owner_id, title, location, address, rent, deposit,
                    bedrooms, bathrooms, furnishing, description, image, status, approved
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            """, (
                owner_id, title, location, address, rent_val, deposit_val,
                bedrooms_val, bathrooms_val, furnishing, description, image_filename, status
            ))

        conn.close()
        flash('House listing added successfully!', 'success')
        return redirect(url_for('owner_dashboard'))

    return render_template('add_house.html')


@app.route('/owner/edit-house/<int:house_id>', methods=['GET', 'POST'])
@login_required
@role_required(['owner'])
def edit_house(house_id):
    """
    Edit existing house details and update image if desired.
    """
    owner_id = session.get('user_id')
    conn = get_db_connection()

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM houses WHERE id = %s AND owner_id = %s", (house_id, owner_id))
        house = cursor.fetchone()

        if not house:
            conn.close()
            flash('Listing not found or you do not have permission to edit it.', 'danger')
            return redirect(url_for('owner_dashboard'))

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            location = request.form.get('location', '').strip()
            address = request.form.get('address', '').strip()
            rent = request.form.get('rent', '').strip()
            deposit = request.form.get('deposit', '').strip()
            bedrooms = request.form.get('bedrooms', '').strip()
            bathrooms = request.form.get('bathrooms', '').strip()
            furnishing = request.form.get('furnishing', 'Furnished')
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'Available')

            try:
                rent_val = float(rent)
                deposit_val = float(deposit)
                bedrooms_val = int(bedrooms)
                bathrooms_val = int(bathrooms)
            except ValueError:
                conn.close()
                flash('Invalid numbers provided for rent or bedrooms.', 'danger')
                return render_template('edit_house.html', house=house)

            # Optional new image upload
            image_filename = house['image']
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '' and allowed_file(file.filename):
                    sec_filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    image_filename = f"house_{owner_id}_{timestamp}_{sec_filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

            cursor.execute("""
                UPDATE houses 
                SET title = %s, location = %s, address = %s, rent = %s, deposit = %s,
                    bedrooms = %s, bathrooms = %s, furnishing = %s, description = %s,
                    image = %s, status = %s
                WHERE id = %s AND owner_id = %s
            """, (
                title, location, address, rent_val, deposit_val,
                bedrooms_val, bathrooms_val, furnishing, description,
                image_filename, status, house_id, owner_id
            ))

            conn.close()
            flash('House details updated successfully!', 'success')
            return redirect(url_for('owner_dashboard'))

    conn.close()
    return render_template('edit_house.html', house=house)


@app.route('/owner/delete-house/<int:house_id>', methods=['POST'])
@login_required
@role_required(['owner'])
def delete_house(house_id):
    """
    Delete a house listing owned by the logged-in owner.
    """
    owner_id = session.get('user_id')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM houses WHERE id = %s AND owner_id = %s", (house_id, owner_id))
    conn.close()
    flash('House listing deleted successfully.', 'info')
    return redirect(url_for('owner_dashboard'))


@app.route('/owner/toggle-status/<int:house_id>', methods=['POST'])
@login_required
@role_required(['owner'])
def owner_toggle_status(house_id):
    """
    Toggle house status between 'Available' and 'Rented'.
    """
    owner_id = session.get('user_id')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT status FROM houses WHERE id = %s AND owner_id = %s", (house_id, owner_id))
        house = cursor.fetchone()
        if house:
            new_status = 'Rented' if house['status'] == 'Available' else 'Available'
            cursor.execute("UPDATE houses SET status = %s WHERE id = %s", (new_status, house_id))
            flash(f'Property status updated to {new_status}.', 'success')
        else:
            flash('Property not found.', 'danger')
    conn.close()
    return redirect(url_for('owner_dashboard'))


@app.route('/owner/requests')
@login_required
@role_required(['owner'])
def owner_requests():
    """
    Owner views all incoming rental requests for their properties.
    """
    owner_id = session.get('user_id')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT r.*, h.title AS house_title, h.location, h.rent, h.deposit, h.image AS house_image,
                   u.name AS tenant_name, u.email AS tenant_email, u.phone AS tenant_phone
            FROM rental_requests r
            JOIN houses h ON r.house_id = h.id
            JOIN users u ON r.tenant_id = u.id
            WHERE h.owner_id = %s
            ORDER BY r.request_date DESC
        """, (owner_id,))
        requests_list = cursor.fetchall()

    conn.close()
    return render_template('requests.html', requests=requests_list)


@app.route('/owner/request/<int:req_id>/<action>', methods=['POST'])
@login_required
@role_required(['owner'])
def owner_handle_request(req_id, action):
    """
    Accept or Reject a tenant rental request:
    - If accepted: change request status to 'Accepted' and mark house status as 'Rented'.
    - If rejected: change request status to 'Rejected'.
    """
    owner_id = session.get('user_id')
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Check that this request belongs to one of the owner's houses
        cursor.execute("""
            SELECT r.*, h.id AS house_id, h.title AS house_title 
            FROM rental_requests r
            JOIN houses h ON r.house_id = h.id
            WHERE r.id = %s AND h.owner_id = %s
        """, (req_id, owner_id))
        req_data = cursor.fetchone()

        if not req_data:
            conn.close()
            flash('Request not found or access unauthorized.', 'danger')
            return redirect(url_for('owner_requests'))

        if action == 'accept':
            # Mark request as Accepted
            cursor.execute("UPDATE rental_requests SET status = 'Accepted' WHERE id = %s", (req_id,))
            # Mark house as Rented
            cursor.execute("UPDATE houses SET status = 'Rented' WHERE id = %s", (req_data['house_id'],))
            flash(f'Rental request #{req_id} accepted! The property has been marked as Rented.', 'success')
        elif action == 'reject':
            cursor.execute("UPDATE rental_requests SET status = 'Rejected' WHERE id = %s", (req_id,))
            flash(f'Rental request #{req_id} rejected.', 'info')
        else:
            flash('Invalid action specified.', 'danger')

    conn.close()
    return redirect(url_for('owner_requests'))


# ----------------------------------------------------------------------------
# 5. ADMIN MODULE ROUTES
# ----------------------------------------------------------------------------
@app.route('/admin/dashboard')
@login_required
@role_required(['admin'])
def admin_dashboard():
    """
    Admin Dashboard:
    Displays 7 required system statistics:
    - Total Users
    - Total Owners
    - Total Tenants
    - Total Houses
    - Available Houses
    - Rented Houses
    - Pending Requests
    Also renders management tables for all users and all houses.
    """
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Statistics queries
        cursor.execute("SELECT COUNT(*) AS cnt FROM users;")
        total_users = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'owner';")
        total_owners = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'tenant';")
        total_tenants = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM houses;")
        total_houses = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM houses WHERE status = 'Available';")
        available_houses = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM houses WHERE status = 'Rented';")
        rented_houses = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM rental_requests WHERE status = 'Pending';")
        pending_requests = cursor.fetchone()['cnt']

        # Fetch all users
        cursor.execute("SELECT id, name, email, phone, role, created_at FROM users ORDER BY id ASC;")
        users_list = cursor.fetchall()

        # Fetch all houses with owner details
        cursor.execute("""
            SELECT h.*, u.name AS owner_name, u.email AS owner_email 
            FROM houses h
            JOIN users u ON h.owner_id = u.id
            ORDER BY h.created_at DESC;
        """)
        houses_list = cursor.fetchall()

    conn.close()

    stats = {
        'total_users': total_users,
        'total_owners': total_owners,
        'total_tenants': total_tenants,
        'total_houses': total_houses,
        'available_houses': available_houses,
        'rented_houses': rented_houses,
        'pending_requests': pending_requests
    }

    return render_template(
        'admin_dashboard.html',
        stats=stats,
        users=users_list,
        houses=houses_list
    )


@app.route('/admin/requests')
@login_required
@role_required(['admin'])
def admin_requests():
    """
    Admin views all rental requests across the entire system.
    """
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT r.*, h.title AS house_title, h.location, h.rent, h.deposit, h.image AS house_image,
                   t.name AS tenant_name, t.email AS tenant_email, t.phone AS tenant_phone,
                   o.name AS owner_name, o.email AS owner_email
            FROM rental_requests r
            JOIN houses h ON r.house_id = h.id
            JOIN users t ON r.tenant_id = t.id
            JOIN users o ON h.owner_id = o.id
            ORDER BY r.request_date DESC;
        """)
        all_requests = cursor.fetchall()

    conn.close()
    return render_template('requests.html', requests=all_requests)


@app.route('/admin/toggle-approval/<int:house_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_toggle_approval(house_id):
    """
    Admin approves or revokes house listing approval.
    """
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT approved FROM houses WHERE id = %s", (house_id,))
        house = cursor.fetchone()
        if house:
            new_appr = 0 if house['approved'] == 1 else 1
            cursor.execute("UPDATE houses SET approved = %s WHERE id = %s", (new_appr, house_id))
            flash('House approval status updated.', 'success')
        else:
            flash('House listing not found.', 'danger')
    conn.close()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete-house/<int:house_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_delete_house(house_id):
    """
    Admin permanently deletes a house listing.
    """
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM houses WHERE id = %s", (house_id,))
    conn.close()
    flash('House listing removed by Administrator.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_delete_user(user_id):
    """
    Admin deletes a registered user (cannot delete own account).
    """
    if user_id == session.get('user_id'):
        flash('You cannot delete your own admin account.', 'danger')
        return redirect(url_for('admin_dashboard'))

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.close()
    flash('User account and related data successfully removed.', 'info')
    return redirect(url_for('admin_dashboard'))


# ----------------------------------------------------------------------------
# Agentic AI Routes & Intelligence APIs
# ----------------------------------------------------------------------------
@app.route('/ai-agent')
def ai_studio():
    """
    Dedicated AI Agent Studio & Command Center.
    Enables interactive property search, multi-property comparisons, 
    owner listing optimization, and rental advisory.
    """
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id, title, location, rent, bedrooms, bathrooms, furnishing, image 
            FROM houses 
            WHERE status = 'Available' AND approved = 1 
            ORDER BY id ASC LIMIT 6
        """)
        featured_houses = cursor.fetchall()
        for h in featured_houses:
            h['rent'] = float(h['rent'])
    conn.close()
    return render_template('ai_studio.html', featured_houses=featured_houses)


@app.route('/api/ai/chat', methods=['POST'])
def ai_chat_endpoint():
    """
    Agentic ReAct endpoint: Accepts user messages, initiates multi-step reasoning,
    executes dynamic database tools, and returns structured thought traces and recommendations.
    """
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    context = {
        'user_id': session.get('user_id'),
        'role': session.get('role'),
        'user_name': session.get('name')
    }

    try:
        response_data = ai_agent.run(message, context=context)
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e), 'answer': f'Agent error: {str(e)}'}), 500


@app.route('/api/ai/estimate-rent', methods=['POST'])
def ai_estimate_rent_endpoint():
    """
    AI Valuation API: Estimates market-appropriate rent and security deposit.
    """
    data = request.get_json() or {}
    location = data.get('location', '')
    bedrooms = data.get('bedrooms', 2)
    furnishing = data.get('furnishing', 'Furnished')
    bathrooms = data.get('bathrooms', 1)

    result = ai_tools.estimate_rent_value(
        location=location,
        bedrooms=bedrooms,
        furnishing=furnishing,
        bathrooms=bathrooms
    )
    return jsonify(result)


@app.route('/api/ai/generate-description', methods=['POST'])
def ai_generate_description_endpoint():
    """
    AI Copywriter API: Produces marketing descriptions and headline suggestions.
    """
    data = request.get_json() or {}
    title = data.get('title', '')
    location = data.get('location', '')
    bedrooms = data.get('bedrooms', 2)
    furnishing = data.get('furnishing', 'Furnished')
    amenities = data.get('amenities', '')

    result = ai_tools.generate_listing_description(
        title=title,
        location=location,
        bedrooms=bedrooms,
        furnishing=furnishing,
        amenities=amenities
    )
    return jsonify(result)


@app.route('/api/ai/match-score', methods=['POST'])
def ai_match_score_endpoint():
    """
    AI Property Matching API: Computes compatibility score for a house given tenant preferences.
    """
    data = request.get_json() or {}
    house_id = data.get('house_id')
    if not house_id:
        return jsonify({'error': 'house_id is required'}), 400

    tenant_pref = {
        'max_rent': data.get('max_rent'),
        'bedrooms': data.get('bedrooms'),
        'furnishing': data.get('furnishing')
    }
    result = ai_tools.calculate_match_score(house_id, tenant_pref)
    return jsonify(result)


@app.route('/api/ai/tools', methods=['GET'])
def ai_tools_manifest_endpoint():
    """
    Returns the declarative manifest of all 13 Agentic AI tools including
    categories, parameter schemas, and example prompts.
    """
    manifest = ai_tools.get_tool_manifest()
    return jsonify({
        'status': 'success',
        'total_tools': len(manifest),
        'tools': manifest
    })


@app.route('/api/ai/execute-tool', methods=['POST'])
def ai_execute_tool_endpoint():
    """
    Dynamic Tool Dispatcher: Executes any registered tool by name with parameters.
    """
    data = request.get_json() or {}
    tool_name = data.get('tool_name')
    if not tool_name:
        return jsonify({'success': False, 'error': 'tool_name parameter is required'}), 400

    parameters = data.get('parameters', {})
    if not isinstance(parameters, dict):
        return jsonify({'success': False, 'error': 'parameters must be a key-value object'}), 400

    # Auto-inject session context if relevant
    if 'user_id' not in parameters and session.get('user_id'):
        parameters['user_id'] = session.get('user_id')
    if 'role' not in parameters and session.get('role'):
        parameters['role'] = session.get('role')
    if 'tenant_name' not in parameters and session.get('name'):
        parameters['tenant_name'] = session.get('name')

    result = ai_tools.execute_tool(tool_name, **parameters)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


@app.route('/api/ai/affordability', methods=['POST'])
def ai_affordability_endpoint():
    """
    Calculates rent affordability, safe ceiling, and upfront capital requirements.
    """
    data = request.get_json() or {}
    income = data.get('monthly_income')
    if not income:
        return jsonify({'error': 'monthly_income is required'}), 400

    target_rent = data.get('target_rent')
    target_deposit = data.get('target_deposit')
    result = ai_tools.calculate_affordability(income, target_rent, target_deposit)
    return jsonify(result)


@app.route('/api/ai/neighborhood-insights', methods=['POST', 'GET'])
def ai_neighborhood_insights_endpoint():
    """
    Returns neighborhood livability ratings, transit, and safety scores.
    """
    if request.method == 'POST':
        data = request.get_json() or {}
        location = data.get('location', 'Indiranagar')
    else:
        location = request.args.get('location', 'Indiranagar')

    result = ai_tools.get_neighborhood_insights(location)
    return jsonify(result)


@app.route('/api/ai/schedule-visit', methods=['POST'])
def ai_schedule_visit_endpoint():
    """
    Schedules an in-person walkthrough and generates a verified ticket.
    """
    data = request.get_json() or {}
    house_id = data.get('house_id')
    if not house_id:
        return jsonify({'error': 'house_id is required'}), 400

    tenant_name = data.get('tenant_name') or session.get('name') or "Applicant"
    tenant_phone = data.get('tenant_phone') or session.get('phone') or "Not Provided"
    visit_date = data.get('visit_date', 'Upcoming Weekend')
    time_slot = data.get('time_slot', '11:00 AM - 01:00 PM')
    notes = data.get('notes', '')

    result = ai_tools.schedule_property_visit(
        house_id=house_id,
        tenant_name=tenant_name,
        tenant_phone=tenant_phone,
        visit_date=visit_date,
        time_slot=time_slot,
        notes=notes
    )
    return jsonify(result)


@app.route('/api/ai/lease-checklist', methods=['POST', 'GET'])
def ai_lease_checklist_endpoint():
    """
    Generates standard rental agreement checklist with 11-month lease best practices.
    """
    if request.method == 'POST':
        data = request.get_json() or {}
        house_id = data.get('house_id')
        rent = data.get('rent')
        deposit = data.get('deposit')
        duration = data.get('duration_months', 11)
    else:
        house_id = request.args.get('house_id')
        rent = request.args.get('rent')
        deposit = request.args.get('deposit')
        duration = int(request.args.get('duration_months', 11))

    result = ai_tools.generate_rental_agreement_checklist(
        house_id=house_id,
        rent=rent,
        deposit=deposit,
        duration_months=duration,
        tenant_name=session.get('name')
    )
    return jsonify(result)


@app.route('/api/ai/platform-stats', methods=['GET'])
def ai_platform_stats_endpoint():
    """
    Returns live marketplace platform statistics.
    """
    result = ai_tools.get_platform_stats()
    return jsonify(result)


@app.route('/api/ai/compare', methods=['POST'])
def ai_compare_endpoint():
    """
    Side-by-side comparison for 1 to 4 properties with auto-benchmark discovery.
    """
    data = request.get_json() or {}
    house_ids = data.get('house_ids', [])
    auto_fill = data.get('auto_fill_similar', True)
    result = ai_tools.compare_properties(house_ids, auto_fill_similar=auto_fill)
    return jsonify(result)




# ----------------------------------------------------------------------------
# Application Bootstrap
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    init_db()
    print("==================================================================")
    print(" House Rental Agent is running at: http://127.0.0.1:5000/")
    print("==================================================================")
    app.run(debug=True, host='127.0.0.1', port=5000)
