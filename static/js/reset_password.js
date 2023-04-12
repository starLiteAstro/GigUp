var password = document.getElementById("newpass");
var confirm_password = document.getElementById("repeatnewpass");
// Front-end validation for reset password form
$(document).ready(function() {
    $('#resetpassform').submit(function(event) {
        if(password.value != confirm_password.value) {
            event.preventDefault();
            confirm_password.setCustomValidity("Passwords do not match.");
        }
    });
});