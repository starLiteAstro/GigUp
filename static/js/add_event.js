// Front-end validation for duration input in "Add an event" form
$(document).ready(function() {
    $('#addeventform').submit(function(event) {
        // Clear all error messages
        $(".error").remove();

        // Get the length of the values of each input
        var hours = document.getElementById("durationhours").value.length;
        var mins = document.getElementById("durationmins").value.length;
        
        // If both fields are empty stop the form from submitting
        if (hours === 0 && mins === 0) {
            event.preventDefault();
            $('#durationmins').after('<span class="error">At least one of either duration in hours or minutes must be filled in.</span>')
        }
    });
});