# House Rental Agent - College Web Application

A clean, responsive, and beginner-friendly web-based **House Rental Management System** built with **Python Flask**, **MySQL**, **HTML5**, **CSS3**, **Vanilla JavaScript**, and **Bootstrap 5**.

This project connects **House Owners**, **Tenants**, and a **System Administrator** in a unified platform to simplify property listing, searching, and rental request processing without unnecessary complexity or third-party paid APIs.

---

## 📋 Table of Contents
1. [Project Overview](#-project-overview)
2. [Key Features by Role](#-key-features-by-role)
3. [Technology Stack](#-technology-stack)
4. [Project Structure](#-project-structure)
5. [Database Schema & Tables Explanation](#-database-schema--tables-explanation)
6. [Prerequisites & Installation](#-prerequisites--installation)
7. [How to Create the MySQL Database](#-how-to-create-the-mysql-database)
8. [How to Run the Application](#-how-to-run-the-application)
9. [Sample Demo Accounts](#-sample-demo-accounts)
10. [Module Walkthrough & Explanations](#-module-walkthrough--explanations)
11. [Viva Voce Questions & Answers (For College Exam)](#-viva-voce-questions--answers)

---

## 🌟 Project Overview
In conventional rental processes, tenants face issues finding verified property information, while house owners struggle to track multiple inquiries. **House Rental Agent** solves this by offering:
- **Direct Owner-Tenant Communication**: Tenants can send inquiries directly for specific homes.
- **Automated Property Status Update**: When an owner accepts a rental request, the property status automatically changes to **"Rented"**.
- **Role-based Authentication & Security**: Password hashing via Werkzeug (`scrypt`), input validation, and session-protected route decorators.
- **Administrative Governance**: Admin monitors platform statistics, approves or revokes listings, and manages registered users.

---

## 👥 Key Features by Role

### 1. 🏠 House Owner
- Register as an Owner and log in securely.
- **Add New House**: Specify title, location, complete address, monthly rent, deposit, bedrooms (BHK), bathrooms, furnishing type, description, and upload a house photo.
- **Manage Houses**: View owned listings, edit existing details, delete listings, and toggle status between `Available` and `Rented`.
- **Manage Rental Requests**: View all tenant requests for listed properties with tenant contact info, and **Accept** or **Reject** requests with one click.

### 2. 👤 Tenant
- Register as a Tenant and browse all verified house listings.
- **Search & Filter**: Filter properties by location, maximum rent budget, and number of bedrooms (1 BHK, 2 BHK, 3 BHK, 4+ BHK).
- **House Details**: View comprehensive property specifications, pictures, amenities, and owner contact details (phone & email).
- **Send Rental Requests**: Submit rental requests with instant `Pending` status.
- **Track Status**: Monitor live statuses (`Pending`, `Accepted`, `Rejected`) and cancel requests from the Tenant Dashboard.

### 3. 🛡️ Administrator
- Secure administrator login.
- **Platform Analytics**: Real-time counters for:
  1. Total Users
  2. Total Owners
  3. Total Tenants
  4. Total Houses
  5. Available Houses
  6. Rented Houses
  7. Pending Rental Requests
- **User Management**: View all registered users with role badges, with capability to delete fraudulent or inactive accounts.
- **Listing Governance**: Moderate property listings by approving or revoking listing status, or deleting spam listings.
- **Audit All Requests**: Inspect every rental transaction across the platform.

---

## 💻 Technology Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, Vanilla JS | Clean semantic layout, responsive behavior, client-side validation |
| **UI Framework** | Bootstrap 5.3 & Bootstrap Icons | Grid layout, responsive navbar, modals, cards, badges |
| **Backend** | Python 3.x with Flask | MVC controller, routing, session handling, business logic |
| **Database** | MySQL (with PyMySQL driver) | Relational database management with foreign keys and cascades |
| **Security** | Werkzeug Security | Industry-standard password hashing (`generate_password_hash`) |

---

## 📂 Project Structure

```text
house-rental-agent/
│
├── app.py                  # Main Flask application with routes and DB logic
├── requirements.txt        # Python package dependencies
├── database.sql            # MySQL database schema & sample seed data
├── README.md               # Complete project documentation & viva guide
│
├── templates/              # HTML5 templates with Jinja2 syntax
│   ├── base.html           # Master layout with responsive navbar & alerts
│   ├── index.html          # Public landing page with hero & featured houses
│   ├── login.html          # Role-based login with one-click demo credentials
│   ├── register.html       # User registration form (Owner / Tenant)
│   ├── houses.html         # Houses catalog with multi-criteria filters
│   ├── house_details.html  # Full house specifications & request button
│   ├── owner_dashboard.html# Owner management panel (Houses, stats, actions)
│   ├── add_house.html      # House submission form with photo upload
│   ├── edit_house.html     # House modification form
│   ├── tenant_dashboard.html # Tenant dashboard showing submitted requests
│   ├── admin_dashboard.html# Admin oversight dashboard with 7 core metrics
│   └── requests.html       # Rental request tables for Owner & Admin
│
└── static/
    ├── css/
    │   └── style.css       # Custom modern CSS styling and animations
    ├── js/
    │   └── script.js       # Auto-dismiss alerts, live image preview, helpers
    └── images/             # House photos and uploaded property images
```

---

## 🗄️ Database Schema & Tables Explanation

The relational database **`house_rental_db`** consists of 3 interrelated tables:

### 1. Table: `users`
Stores registered user credentials and assigned roles.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INT | AUTO_INCREMENT, PRIMARY KEY | Unique user ID |
| `name` | VARCHAR(100) | NOT NULL | User's full name |
| `email` | VARCHAR(100) | NOT NULL, UNIQUE | User email (used for login) |
| `phone` | VARCHAR(20) | NOT NULL | 10-digit contact number |
| `password` | VARCHAR(255) | NOT NULL | Hashed password string |
| `role` | ENUM('admin','owner','tenant') | NOT NULL | Access authorization role |
| `created_at`| TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |

### 2. Table: `houses`
Stores property listings posted by house owners.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INT | AUTO_INCREMENT, PRIMARY KEY | Unique house listing ID |
| `owner_id` | INT | NOT NULL, FOREIGN KEY (`users.id`) ON DELETE CASCADE | ID of owner who listed the house |
| `title` | VARCHAR(200) | NOT NULL | House title / headline |
| `location` | VARCHAR(100) | NOT NULL | Area / locality / city |
| `address` | TEXT | NOT NULL | Full postal address |
| `rent` | DECIMAL(10,2) | NOT NULL | Monthly rent amount |
| `deposit` | DECIMAL(10,2) | NOT NULL | Security deposit amount |
| `bedrooms` | INT | NOT NULL | Number of bedrooms (BHK) |
| `bathrooms`| INT | NOT NULL | Number of bathrooms |
| `furnishing`| ENUM('Furnished','Semi-Furnished','Unfurnished') | NOT NULL | Furnishing condition |
| `description`| TEXT | NULL | Detailed amenities and remarks |
| `image` | VARCHAR(255) | DEFAULT 'default_house.jpg' | Saved image filename |
| `status` | ENUM('Available','Rented') | DEFAULT 'Available' | Current availability status |
| `approved` | TINYINT(1) | DEFAULT 1 | Admin approval status (1=Approved, 0=Pending) |
| `created_at`| TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Listing post timestamp |

### 3. Table: `rental_requests`
Stores rental inquiries made by tenants for specific houses.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INT | AUTO_INCREMENT, PRIMARY KEY | Unique request ID |
| `house_id` | INT | NOT NULL, FOREIGN KEY (`houses.id`) ON DELETE CASCADE | ID of requested house |
| `tenant_id` | INT | NOT NULL, FOREIGN KEY (`users.id`) ON DELETE CASCADE | ID of tenant requesting house |
| `status` | ENUM('Pending','Accepted','Rejected') | DEFAULT 'Pending' | Current status of request |
| `request_date`| TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Timestamp when requested |

---

## ⚙️ Prerequisites & Installation

### Step 1: Install Python
Ensure Python 3.8 or higher is installed:
```bash
python --version
```

### Step 2: Install Required Packages
Navigate to the project directory and install dependencies:
```bash
cd house-rental-agent
pip install -r requirements.txt
```

---

## 🗄️ How to Create the MySQL Database

### Option A: Using MySQL Command Line (Recommended)
1. Open Command Prompt or PowerShell.
2. Log into MySQL:
   ```bash
   mysql -u root -p
   ```
3. Run the SQL script:
   ```sql
   source C:/path/to/house-rental-agent/database.sql;
   ```
   *(Or on Windows PowerShell)*:
   ```powershell
   Get-Content database.sql -Raw | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
   ```

### Option B: Using MySQL Workbench
1. Open **MySQL Workbench** and connect to your local MySQL server.
2. Go to **File -> Open SQL Script...** and select `database.sql`.
3. Click the **Execute (⚡ Lightning icon)** to run the entire script.
4. Refresh your Schemas navigator to see `house_rental_db` with `users`, `houses`, and `rental_requests`.

### Option C: Using XAMPP / phpMyAdmin
1. Open XAMPP Control Panel and start **Apache** and **MySQL**.
2. Open your browser and go to `http://localhost/phpmyadmin/`.
3. Click on the **Import** tab at the top.
4. Choose the `database.sql` file from your project folder and click **Import / Go**.

---

## 🚀 How to Run the Application

1. Verify or set your database credentials in `app.py` (or via environment variables):
   - Default Host: `localhost`
   - Default Port: `3306`
   - Default User: `root`
   - Default Password: `root` *(adjust if your local MySQL has a different password or empty password)*
   - Database: `house_rental_db`

2. Start the Flask application:
   ```bash
   python app.py
   ```

3. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

---

## 🔑 Sample Demo Accounts

All accounts are pre-seeded in `database.sql` with hashed passwords:

| Role | Email | Password | Name |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@example.com` | `admin123` | System Administrator |
| **House Owner** | `owner@example.com` | `owner123` | Rajesh Kumar |
| **Tenant** | `tenant@example.com` | `tenant123` | Ananya Sharma |

> **College Viva Tip:** On the Login page (`/login`), you can click the convenient **Admin**, **Owner**, or **Tenant** demo buttons to instantly populate the credentials for quick testing!

---

## 🔍 Module Walkthrough & Explanations

### 1. Home Page (`/`)
- Hero section with prominent title: *"Find Your Perfect Rental Home"*.
- Quick search bar allowing immediate filtering by location and bedrooms.
- Displays featured available houses fetched directly from MySQL.
- Seamless navigation buttons for login and registration.

### 2. Authentication Module (`/login`, `/register`, `/logout`)
- Secure registration capturing Name, Email, Phone, Password, and Role (`Owner` / `Tenant`).
- Passwords are encrypted using Werkzeug's `generate_password_hash`.
- Login validates the password hash with `check_password_hash` and checks that the selected role matches the registered role.
- Session maintains `user_id`, `name`, `email`, and `role` until logout.

### 3. Tenant Module (`/houses`, `/houses/<id>`, `/tenant/dashboard`)
- **Catalog Browsing**: Live multi-criteria filter for location, maximum budget, and bedroom count.
- **House Details**: Complete view with images, deposit, bedrooms, bathrooms, furnishing condition, owner contact information, and a **"Send Rental Request"** button.
- **Tenant Dashboard**: Shows summary cards and an inquiry table tracking all requests with live badges (`Pending`, `Accepted`, `Rejected`) and the ability to cancel pending requests.

### 4. Owner Module (`/owner/dashboard`, `/owner/add-house`, `/owner/requests`)
- **Owner Dashboard**: Displays total properties, available properties, rented properties, and pending requests.
- **Add & Edit House**: Simple form supporting title, locality, address, rent, deposit, specs, and image file upload.
- **Status Toggle**: One-click button to toggle listing availability between `Available` and `Rented`.
- **Requests Management**: Allows owners to review tenant inquiries. When the owner clicks **Accept**, the request status becomes `Accepted` and the house automatically updates to `Rented`.

### 5. Admin Module (`/admin/dashboard`, `/admin/requests`)
- **Summary Metrics**: Displays the 7 system-wide statistics required for platform oversight.
- **House Moderation**: Table of all houses with ability to toggle approval (`Approved` / `Revoke`) or permanently delete listings.
- **User Governance**: Table of all registered accounts with role tags and delete capability (with self-deletion protection).
- **All Requests Audit**: Global view of all rental requests across all owners and tenants.

---

## 🎓 Viva Voce Questions & Answers

**Q1: What architecture does this web application follow?**  
> **Answer:** It follows the **Model-View-Controller (MVC)** architectural pattern:
> - **Model**: MySQL tables (`users`, `houses`, `rental_requests`) managing data persistence.
> - **View**: HTML5 templates rendered via Jinja2 with Bootstrap 5 styling.
> - **Controller**: Flask route handlers in `app.py` managing incoming requests, database interactions, and business logic.

**Q2: How is password security handled?**  
> **Answer:** Passwords are never stored in plain text. We use `werkzeug.security.generate_password_hash` to compute a salted cryptographic hash (`scrypt`). During login, `check_password_hash` verifies the user's password without ever needing to decrypt or store the original password.

**Q3: How are SQL injection attacks prevented?**  
> **Answer:** All database operations use **parameterized queries** with `%s` placeholders (prepared statements) provided by PyMySQL. The database engine separates the SQL syntax from user data, neutralizing malicious SQL injection attempts.

**Q4: How does role-based access control (RBAC) work?**  
> **Answer:** We implemented custom Python decorators: `@login_required` to ensure a valid session exists, and `@role_required(['owner'])` or `@role_required(['admin'])` to inspect `session.get('role')`. If an unauthorized user attempts to access an endpoint, they are redirected with an alert message.

**Q5: What happens when an owner accepts a rental request?**  
> **Answer:** The application runs an update transaction: the request status in `rental_requests` is changed from `'Pending'` to `'Accepted'`, and the associated property in `houses` has its `status` changed from `'Available'` to `'Rented'`.

**Q6: What is the purpose of foreign keys with `ON DELETE CASCADE`?**  
> **Answer:** Foreign keys enforce referential integrity between tables. `ON DELETE CASCADE` ensures that if a user or house is deleted, all dependent records (such as rental requests or listed houses) are automatically removed, preventing orphaned records.
