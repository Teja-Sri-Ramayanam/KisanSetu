/**
 * Kisan Setu - Authentication JavaScript
 * Handles role card selection, dynamic form fields, and validations.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Role Selection Cards
    const roleOptions = document.querySelectorAll('.role-card-option');
    const roleInput = document.getElementById('selected_role_input');

    if (roleOptions.length > 0 && roleInput) {
        roleOptions.forEach(card => {
            card.addEventListener('click', () => {
                roleOptions.forEach(c => c.classList.remove('active'));
                card.classList.add('active');
                const roleValue = card.getAttribute('data-role');
                roleInput.value = roleValue;

                // Toggle role-specific fields if on registration page
                toggleRoleFields(roleValue);
            });
        });

        // Initialize based on preset role or first active card
        const initialRole = roleInput.value || (document.querySelector('.role-card-option.active')?.getAttribute('data-role')) || 'Farmer';
        roleInput.value = initialRole;
        const matchingCard = document.querySelector(`.role-card-option[data-role="${initialRole}"]`);
        if (matchingCard) {
            roleOptions.forEach(c => c.classList.remove('active'));
            matchingCard.classList.add('active');
        }
        toggleRoleFields(initialRole);
    }

    function toggleRoleFields(role) {
        const farmerFields = document.querySelectorAll('.role-field-farmer');
        const officerFields = document.querySelectorAll('.role-field-officer');
        const adminFields = document.querySelectorAll('.role-field-admin');

        farmerFields.forEach(el => el.style.display = (role === 'Farmer') ? 'block' : 'none');
        officerFields.forEach(el => el.style.display = (role === 'Procurement Officer') ? 'block' : 'none');
        adminFields.forEach(el => el.style.display = (role === 'Admin') ? 'block' : 'none');

        const officerCenterSelect = document.getElementById('assigned_center_id');
        if (officerCenterSelect) {
            officerCenterSelect.required = (role === 'Procurement Officer');
        }

        const adminKeyInput = document.getElementById('admin_key');
        if (adminKeyInput) {
            adminKeyInput.required = (role === 'Admin');
        }
    }

    // 2. Client-side Form Validation
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', (e) => {
            const pwd = document.getElementById('password')?.value;
            const confirmPwd = document.getElementById('confirm_password')?.value;
            const role = roleInput ? roleInput.value : '';

            if (!role) {
                e.preventDefault();
                showToast("Please select your account role.", "warning");
                return;
            }

            if (pwd !== confirmPwd) {
                e.preventDefault();
                showToast("Passwords do not match! Please check.", "danger");
                return;
            }

            if (pwd && pwd.length < 6) {
                e.preventDefault();
                showToast("Password must be at least 6 characters.", "warning");
                return;
            }
        });
    }
});
