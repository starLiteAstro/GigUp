// Show or hide validation popup based on whether or not user is focussed on username or password input box
$(document).ready(function(){
    $('#passwd').focus(function(){
        $('#message').css("visibility", "visible");
    }).focusout(function(){
        $('#message').css("visibility", "hidden");
    });

    $('#uname').focus(function(){
        $('#message').css("visibility", "visible");
    }).focusout(function(){
        $('#message').css("visibility", "hidden");
    });

});

window.onload = function() {
    var unameInput = document.getElementById("uname");
    var passInput = document.getElementById("passwd");
    var letter = document.getElementById("letter");
    var capital = document.getElementById("capital");
    var number = document.getElementById("number");
    var length = document.getElementById("length");

    // Change icons when username changes validity
    unameInput.onkeyup = function() {
        if (unameInput.value.length >= 3 && unameInput.value.length <= 20) {
            unamelength.classList.remove("invalid");
            unamelength.classList.add("valid");
        } else {
            unamelength.classList.remove("valid");
            unamelength.classList.add("invalid");
        }
    }

    // Change icons when password changes validity
    passInput.onkeyup = function() {
        // Validate lowercase letters
        var lowerCaseLetters = /[a-z]/g;
        if(passInput.value.match(lowerCaseLetters)) {  
            letter.classList.remove("invalid");
            letter.classList.add("valid");
        } else {
            letter.classList.remove("valid");
            letter.classList.add("invalid");
        }
    
        // Validate capital letters
        var upperCaseLetters = /[A-Z]/g;
        if(passInput.value.match(upperCaseLetters)) {  
            capital.classList.remove("invalid");
            capital.classList.add("valid");
        } else {
            capital.classList.remove("valid");
            capital.classList.add("invalid");
        }

        // Validate numbers
        var numbers = /[0-9]/g;
        if(passInput.value.match(numbers)) {  
            number.classList.remove("invalid");
            number.classList.add("valid");
        } else {
            number.classList.remove("valid");
            number.classList.add("invalid");
        }
    
        // Validate length
        if(passInput.value.length >= 8) {
            length.classList.remove("invalid");
            length.classList.add("valid");
        } else {
            length.classList.remove("valid");
            length.classList.add("invalid");
        }
    }
}