document.addEventListener("DOMContentLoaded", function() {
    const registerForm = document.getElementById("registerForm");

    if (registerForm) {
        registerForm.addEventListener("submit", function(event) {
            const password = registerForm.querySelector("[name='password']").value;
            if (password.length < 6) {
                alert("Password must be at least 6 characters!");
                event.preventDefault();
            }
        });
    }
});

// Copy referral link to clipboard
function copyReferralLink(referralCode) {
    const link = `${window.location.origin}/register?referral_code=${referralCode}`;
    navigator.clipboard.writeText(link)
        .then(() => alert("Referral link copied to clipboard!"))
        .catch(err => alert("Failed to copy link: " + err));
}

// Toggle sidebar visibility
document.addEventListener('DOMContentLoaded', () => {
    const toggleButton = document.getElementById('toggleSidebar');
    const sidebar = document.getElementById('sidebar');

    toggleButton?.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
    });
});
