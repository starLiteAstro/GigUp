// Close flash popups
function closeFlash() {
    var flashes = document.getElementsByClassName("flashes");
    for (var i = 0; i < flashes.length; i++) {
        flashes[i].style.display = "none";
    }
}

// Close Notifications asynchronously
function closeNotif(id) {
    var data = {"notifid": id} // Send Notification ID as a JSON object
    xhttp = new XMLHttpRequest();
    xhttp.open('POST', '/delete_notif', true);
    xhttp.setRequestHeader('content-type', 'application/json');
    xhttp.onreadystatechange = function() {
        if (xhttp.readyState == 4 && xhttp.status == 200) {
            var notif = document.getElementById(id); // If request successful, hide Notification box
            notif.style.display = "none";
        }
    }
    xhttp.send(
        JSON.stringify(data)
    )
}

setTimeout(function() {
    $('#flash').delay(5000).fadeOut(1000);
    $('#error').delay(5000).fadeOut(1000);
})