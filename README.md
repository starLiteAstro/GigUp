![logo](/static/images/gigup-logo-wide.png)

# GigUp Readme

This readme goes through the basic features of the website, describes assumptions I had to take in regards to the specification and optional features that I included.

## Header and footer
A header and footer are always present on the screen for ease of navigation though the website. The footer contains an about and credits page typical in many websites. The header contains links to events, register and login for non-logged in users, while logged-in attendees will have a 'My tickets' tab showing owned/cancelled tickets. Organisers can access two more tabs, 'My events' for managing created events or events that they have been promoted to by another Organiser, and 'Add an event' to add an event.


## Home page
The home page shows the three most recently added events, with a link to show more events. This gives the the home page a sense of uniqueness, as this cannot be seen anywhere else on the site. When events are near full capacity, up to three will be shown at the the home page so that new visitors will have a increased chance to book an event.


## Registering and verifying a user
When a user registers, they must fill in the form with their unique email, unique username and password. If they know the code to become an Organiser, they can input this in the 'Organiser access' field to immediately become an Organiser when they register. The form also includes a 'sign in' button, which directs the user to the login screen. A box showing requirements for a username and password are shown on the right hand side when the user is focussed on the username or password box, changing dynamically when the user makes changes to validity. This gives the user a clear indicator of how secure their password needs to be.
When a user registers for the first time, an email will be sent to their email address. This contains a link to verify themselves which will allow them to book tickets. For security, the link in question is made up of a token which is a UUID value stored in the user's model. When a user successfully verifies themselves, the token will be removed from their model.

## Logging in a user
Any user who registers for the first time will also bypass logging in. When a user logs out, they can only access their account by logging in (or using the 'forgot password' feature). To log in, the user requires a username and password they registered with. If the user does not have an account, they can register using the 'register' button below the form, included for ease of access.

## Forgot password feature
If the user forgot their password, they can press the 'forgot password' button on the login page. This directs them to a form where they must provide the email address they registered with. This will send an email to verify the user, similar to the verification process on registration. When the link is pressed, they are directed to a form to enter a new password, and repeat it for added security, where on success they will be logged in.

## Viewing events
The 'Events' page shows all events, sorted by upcoming and past (non-cancelled) events and cancelled events, each sorted by latest date of the event first. In each event box is the event's name, date and time, location, description and duration. Attendees and organisers are able to book tickets for each event, while only organisers can see the capacity and remaining spaces whenever they wish. For non-organisers, the event capacity and remaining tickets (in the form 'x ticket(s) left!') will only show when the event is at less than 5% capacity remaining. When the event is fully booked, the word 'FULL!' will appear on the event. Note that this only applies to upcoming events, as past and cancelled events will always show the capacity.

## User account settings
Account settings are located on the far right of the header. In there the user's username and role is shown, and the user can set a custom profile picture, which gives the site a sense of community. There is also the option to change the user's username, provided it is different and unique. It is also where the user can log out and delete their account, which will remove all related data from the server.

## Notifications feature
Attendees of events are notified of any cancellations (with a given reason from the organiser) via the notification tab. This will update with a number on the side showing the number of new notifications whenever a new notification has been posted, after the user refreshes the webpage. Organisers will also be notified when an event is at near capacity and full. Notifications can be removed, which is done asynchronously using AJAX, giving a more fluid appeal.

## Adding, managing and cancelling events
One major benefit of being an organiser is the ability to add new events. Events must require a name, date, duration (either in hours or minutes or both but not neither), capacity and location. A description and image is also optional. The form can be easil reset by pressing the 'reset' button at the bottom.
There is also the ability to add any other user as an organiser of this event, meaning they can manage and change the specific event. An attendee who is promoted as an organiser has all the powers of an organiser. They also have the ability to add a new event, but can only manage events that they have created or events that they were promoted to by other organisers.
When an event is added for the first time, there is the option to change any details, except for the date and time of the event. This is done by clicking the 'manage event' button. The minimum capacity allowed for the event depends on how many tickets are currently booked for that event: if it is less than 5 then the minimum is 5; if it is greater than 5 then the minimum is the number of booked tickets.
Note that the date of the event's creation is shown on the 'My events' page - this can only be seen on events the user has created. Also, any organiser of an event will be able to cancel the event, before providing a reason. Although this may not be the safest approach since the once-attendee organiser can cancel the event without permission of the event's creator, it is assumed that organisers who promote attendees to organisers already have a great deal of trust beforehand. Cancellation messages are sent to all attendees and organisers as notifications.

## Booking and cancelling tickets
Attendees are only allowed to book from one to five tickets (until the event reaches 5 or less remaining spaces, whereby users can only up to the maximum), while organisers can book up to the maximum capacity. Every ticket the user has booked, shown on the 'my tickets' page, consists of the name of the user who booked it, the date it was booked, the name, date, location, duration, and capacity of the event, with an optional description or image. Each ticket also contains a unique barcode, created from the ticket's ID.
Tickets can expire when the event expires (i.e. when the current time has passed the date of the event. Tickets can also be cancelled prematurely, either individually in 'my tickets' or completely for a single event in 'my events'. Note that tickets nor events cannot be completely deleted, only cancelled.

## Accessibility
I believe that my website is accessible to people with disabilities, as most buttons used have thick padding and webpages can be traversed with the TAB key. The website contains no flashing images, and I have tried to make the colour scheme appealing as well as accessible. A reasonable font size was used in all parts of the website.

## JavaScript and jQuery
For some functions of the website, I used JavaScript and jQuery to make it feel more dynamic. For instance, whenever a popup message displays at the top of the page, it will stay there for 5 seconds and then fade out, unless if the user decides to close it earlier. This was achieved with the setTimeout() method used in JS and jQuery which allows the execution of code after a certain amount of time. The 'delete account' button, when pressed, will load up a second confirmation button in the form of a modal, which floats over the webpage. This was done with a mixture of the JS onClick() method and CSS. The asynchronous 'closing' of notifications was achieved with AJAX, which, when the 'close notification' button was clicked, sent a JSON object requested by Flask containing the ID of the notification, allowing it to be deleted on the backend.

## Validation and security
Validation was performed both on the front and back-end. This was so that the website could be as secure as possible from any breaches. Passwords were stored as hashes, not as their plaintext since it would be extremely dangerous to users otherwise in the event of an attack.
