// Open the "delete account" modal popup
function openModal() {
    var modal = document.getElementById("deleteform");
    modal.style.display = "block";
}

// Close the "delete account" modal popup
function closeModal() {
    var modal = document.getElementById("deleteform");
    modal.style.display = "none";
}

// If window outside modal is clicked when modal is open, close modal
window.onclick = function(event) {
    var modal = document.getElementById("deleteform");
    if (event.target == modal) {
        modal.style.display = "none";
    }
}

// Front-end validation for changing username
$(document).ready(function() {
    $('#updatename').submit(function() {
        var validates = true
        var username = $('#username').val();

        $(".error").remove();

        if (username.length < 3 || username.length > 20) {
            $('#uname').after('<span class="error">Username must between 3 and 20 characters.</span>')
            validates = false;
        }

        return validates;
    });
});