document.addEventListener("DOMContentLoaded", () => {
    // Ensure all elements exist before attempting to access them
    const bankNameInput = document.getElementById("bankNameInput");
    const accountNumberInput = document.getElementById("accountNumberInput");
    const accountNameInput = document.getElementById("accountNameInput");
    const saveButton = document.getElementById("saveButton");
    const editButton = document.getElementById("editButton");
    const removeButton = document.getElementById("removeButton");
    const tooltip = document.getElementById("tooltip");

    if (!bankNameInput || !accountNumberInput || !accountNameInput || !saveButton || !editButton || !removeButton) {
        console.error("One or more elements are missing in the DOM.");
        return;
    }

    const userId = document.getElementById("userId").value;

    // Fetch the user's bank details status
    fetch(`/check-bank-details?user_id=${userId}`)
        .then((response) => response.json())
        .then((data) => {
            if (data.has_bank_details) {
                // Disable input fields and save button if bank details exist
                bankNameInput.disabled = true;
                accountNumberInput.disabled = true;
                accountNameInput.disabled = true;
                saveButton.disabled = true;

                // Set placeholders to existing bank details
                bankNameInput.placeholder = data.bank_details.bank_name || "Bank Name";
                accountNumberInput.placeholder = data.bank_details.account_number || "Account Number";
                accountNameInput.placeholder = data.bank_details.account_name || "Account Name";

                // Show the edit button and tooltip
                editButton.style.display = "block";
                removeButton.style.display = "block";
                tooltip.style.display = "block";
            } else {
                // Enable input fields and save button if no bank details exist
                bankNameInput.disabled = false;
                accountNumberInput.disabled = false;
                accountNameInput.disabled = false;
                saveButton.disabled = false;

                // Clear placeholders
                bankNameInput.placeholder = "Enter Bank Name";
                accountNumberInput.placeholder = "Enter Account Number";
                accountNameInput.placeholder = "Enter Account Name";

                // Hide the edit button and tooltip
                editButton.style.display = "none";
                removeButton.style.display = "none";
                tooltip.style.display = "none";
            }
        })
        .catch((error) => {
            console.error("Error checking bank details:", error);
        });
});










document.addEventListener("DOMContentLoaded", function () {
    const editButton = document.getElementById("editButton");
    const modal = document.getElementById("editModal");
    const closeButton = document.getElementsByClassName("close")[1];
    const editForm = document.getElementById("editForm");
    const bankNameInput = document.getElementById("mbankNameInput");
    const accountNumberInput = document.getElementById("maccountNumberInput");
    const accountNameInput = document.getElementById("maccountNameInput");

    const userId = document.getElementById("userId").value;

    // Open modal when edit button is clicked
    editButton.addEventListener("click", function () {
        modal.style.display = "block";

        // Fetch the user's bank details status
        fetch(`/check-bank-details?user_id=${userId}`)
        .then((response) => response.json())
        .then((data) => {
            if (data.has_bank_details) {
                // Set placeholders to existing bank details
                bankNameInput.placeholder = data.bank_details.bank_name || "Bank Name";
                accountNumberInput.placeholder = data.bank_details.account_number || "Account Number";
                accountNameInput.placeholder = data.bank_details.account_name || "Account Name";

            
            } else {
                // Enable input fields and save button if no bank details exist

                // Clear placeholders
                bankNameInput.placeholder = "Enter Bank Name";
                accountNumberInput.placeholder = "Enter Account Number";
                accountNameInput.placeholder = "Enter Account Name";
            }
        })
        .catch((error) => {
            console.error("Error checking bank details:", error);
        });




        
    });

    // Close modal when close button is clicked
    closeButton.addEventListener("click", function () {
        modal.style.display = "none";
    });

    // Close modal when clicking anywhere outside the modal content
    window.addEventListener("click", function (event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    });

});












document.addEventListener("DOMContentLoaded", function () {
    const removeButton = document.getElementById("removeButton");
    const removeModal = document.getElementById("removeBankModal");
    const cancelRemoveBank = document.getElementById("cancelRemoveBank");
    const confirmRemoveButton = document.getElementById("confirmRemoveButton");

    removeButton.addEventListener("click", function () {
        removeModal.style.display = "block";
    });

    cancelRemoveBank.addEventListener("click", function () {
        removeModal.style.display = "none";
    });

    // Handle the removal of bank details
    confirmRemoveButton.addEventListener("click", function () {
        fetch("/remove-bank-details", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            credentials: "same-origin", // Ensure cookies/session are sent
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert("Bank details removed successfully.");
                    // Optionally, reload the page or update UI dynamically
                    location.reload();
                } else {
                    alert(data.message || "Failed to remove bank details.");
                }
            })
            .catch(error => {
                console.error("Error:", error);
                alert("An error occurred while removing bank details.");
            });
    });

    // Close modal when clicking anywhere outside the modal content
    window.addEventListener("click", function (event) {
        if (event.target == removeModal) {
            removeModal.style.display = "none";
        }
    });
});
