/**
 * House Rental Agent - Client-side JavaScript
 * Beginner-friendly helper utilities for interactivity, preview, and validation
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Auto-dismiss flash alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // 2. Image upload preview for Add/Edit House forms
    const imageInput = document.getElementById('houseImageInput');
    const imagePreview = document.getElementById('imagePreview');
    if (imageInput && imagePreview) {
        imageInput.addEventListener('change', function () {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    imagePreview.src = e.target.result;
                    imagePreview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // 3. Client-side number guard (prevent negative rent / deposit)
    const rentInput = document.getElementById('rentInput');
    const depositInput = document.getElementById('depositInput');
    [rentInput, depositInput].forEach(input => {
        if (input) {
            input.addEventListener('input', function () {
                if (parseFloat(this.value) < 0) {
                    this.value = 0;
                }
            });
        }
    });

    // 4. Quick Demo Login Fillers (Great for College Viva Presentations!)
    window.fillDemoLogin = function(role) {
        const emailInput = document.getElementById('email');
        const passwordInput = document.getElementById('password');
        const roleSelect = document.getElementById('role');

        if (!emailInput || !passwordInput) return;

        if (role === 'admin') {
            emailInput.value = 'admin@example.com';
            passwordInput.value = 'admin123';
            if (roleSelect) roleSelect.value = 'admin';
        } else if (role === 'owner') {
            emailInput.value = 'owner@example.com';
            passwordInput.value = 'owner123';
            if (roleSelect) roleSelect.value = 'owner';
        } else if (role === 'tenant') {
            emailInput.value = 'tenant@example.com';
            passwordInput.value = 'tenant123';
            if (roleSelect) roleSelect.value = 'tenant';
        }
    };
});
