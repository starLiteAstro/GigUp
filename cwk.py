# import Flask, SQLAlchemy, flask_login, werkzeug and datetime
import datetime
import os
import re
import uuid
from io import BytesIO

from barcode import EAN13
from barcode.writer import SVGWriter
from flask import Flask, Markup, flash, jsonify, redirect, render_template, request
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from markupsafe import escape
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from werkzeug import security
from werkzeug.utils import secure_filename

app = Flask(__name__)
mail = Mail(app)

UPLOAD_FOLDER = "static/"
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg", "gif"])

# Select the database filename
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///todo.sqlite"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1000 * 1000
app.config["MAIL_SUPPRESS_SEND"] = False

app.secret_key = "What a secret!"
app.jinja_env.globals.update(zip=zip)

# Set up a 'model' for the data we want to store
from db_schema import Event, EventOrganiser, Notification, Ticket, User, db, dbinit

# Initialise the database so it can connect with our app
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# Change this to False to avoid resetting the database every time this app is restarted
resetdb = False
if resetdb:
    with app.app_context():
        # Drop everything, create all the tables, then put some data into the tables
        db.drop_all()
        db.create_all()
        dbinit()


# Custom error handlers
@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(410)
def gone(e):
    return render_template("410.html"), 410


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


# Home page
@app.route("/index")
@app.route("/")
def index():
    new_events = Event.query.order_by(desc(Event.created_at)).limit(3).all()
    near_full_events = (
        Event.query.filter_by(is_near_full=True)
        .filter_by(is_full=False)
        .order_by(desc(Event.date))
        .limit(3)
        .all()
    )
    return render_template(
        "index.html", new_events=new_events, near_full_events=near_full_events
    )


# "Register" routes
# Registers a User
@app.route("/registration", methods=["GET", "POST"])
def registration():
    if current_user.is_authenticated:
        return redirect("/index")

    if request.method == "POST":
        email = request.form["email"]
        username = request.form["uname"]
        password = request.form["passwd"]
        organiser_password = request.form["orgpasswd"]
        is_organiser = False
        is_confirmed = False
        avatar = "defaultavatar.png"
        token = None

        # Back-end validation of credentials
        if (
            not re.match(r"[^@]+@[^@]+\.[^@]+", email)
            or len(username) <= 2
            or len(username) >= 21
            or not re.match(r"(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}", password)
        ):
            flash("Invalid credentials!")
            return redirect("/register")

        # Check if organiser password was entered
        organiser_hash = security.generate_password_hash(organiser_password)
        if security.check_password_hash(organiser_hash, "Dc5_G1gz"):
            is_organiser = True
        # Hash password for security
        password_hash = security.generate_password_hash(password)
        # Direct User to login page if they already have an account
        user = User.query.filter_by(email=email).first()
        if user is not None:
            if user.username == username and security.check_password_hash(
                user.password_hash, password
            ):
                flash("Email is already registered. Did you mean to login?")
                return redirect("/login")
            else:
                flash("Email has already been taken.")
                return redirect("/register")

        try:
            # Create a user with their credentials
            new_user = User(
                email=email,
                username=username,
                password_hash=password_hash,
                is_organiser=is_organiser,
                is_confirmed=is_confirmed,
                avatar=avatar,
                token=token,
            )
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError as exc:  # If adding User fails, roll back changes
            db.session.rollback()
            flash("Could not register user.")

        flash("Registered successfully. Please check your mail to verify your account.")
        login_user(new_user)
        send_verify_email()  # Call the verify function

        return redirect("/index")

    else:
        return render_template("register.html")


# Sends verification email to a User during signup
@app.route("/send_verify_email", methods=["GET", "POST"])
@login_required
def send_verify_email():
    if current_user.is_confirmed:
        flash("Already verified.")
        return redirect("/index")

    if request.method == "POST":
        try:
            current_user.token = uuid.uuid4().hex
            db.session.commit()
            msg = Message(
                subject="Verify your GigUp account",
                sender=("GigUp", "gigup-admin@example.com"),
                recipients=[current_user.email],
            )
            msg.html = render_template("verify_message.html")
            # Attach an image to the header
            msg.attach(
                "gigup-logo-mail.png",
                "image/png",
                open(
                    os.path.join(UPLOAD_FOLDER, "images", "gigup-logo-mail.png"), "rb"
                ).read(),
                "inline",
                headers=[["Content-ID", "<MyImage>"]],
            )
            assert msg.sender == "GigUp <gigup-admin@example.com>"
            mail.send(msg)
        except IntegrityError as exc:
            db.session.rollback()
            flash("Verification email could not be sent.")

    return redirect("/index")


# Verifies User by comparing the email link with the User's token
@app.route("/verify/<string:token>", methods=["GET", "POST"])
@login_required
def verify(token):
    if token == current_user.token:
        try:
            current_user.is_confirmed = True  # User is now confirmed
            current_user.token = None
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            flash("Account was unable to be verified.")
        flash("Successfully verified!")
    return redirect("/index")


## Login page routes
# Logs in a User
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if current_user.is_authenticated:
        flash("You are already logged in.")
        return redirect("/index")

    if request.method == "POST":
        username = request.form["uname"]
        password = request.form["passwd"]

        # Find the User with this name
        user = User.query.filter_by(username=username).first()
        if user is None:
            error = "No such user."
        elif not security.check_password_hash(
            user.password_hash, password
        ):  # If given password does not match
            error = "No such user."
        elif error is None:
            # Success, log in user
            flash("Successful login!")
            login_user(user)
            return redirect("/index")

    return render_template("login.html", error=error)


# Loads "forgot password" page
@app.route("/forgot_password")
def forgot_password():
    return render_template("forgot_password.html")


# Sends an email for password verification to the User to verify themselves by comparing link with token
@app.route("/email_reset_password", methods=["GET", "POST"])
def email_reset_password():
    if request.method == "POST":
        email = request.form["email"]
        user = User.query.filter_by(email=email).first()
        if user is None:
            flash("User with given email does not exist.")
        else:
            try:
                user.token = uuid.uuid4().hex  # Set the token as a UUID value
                db.session.commit()
                msg = Message(
                    subject="Reset your GigUp account password",
                    sender=("GigUp", "gigup-admin@example.com"),
                    recipients=[email],
                )
                msg.html = render_template("reset_pwd_message.html", user=user)
                msg.attach(
                    "gigup-logo-mail.png",
                    "image/png",
                    open(
                        os.path.join(UPLOAD_FOLDER, "images", "gigup-logo-mail.png"),
                        "rb",
                    ).read(),
                    "inline",
                    headers=[["Content-ID", "<MyImage>"]],
                )
                assert msg.sender == "GigUp <gigup-admin@example.com>"
                mail.send(msg)
            except IntegrityError as exc:
                db.session.rollback()
                flash("Email could not be sent.")

            flash(
                "Email successfully sent. Please check your mail to reset your password."
            )
    return render_template("login.html")


# Loads the form to reset password after a User clicks the email confirmation link and validates password
@app.route("/reset_password/<string:token>", methods=["POST", "GET"])
def reset_password(token):
    error = ""
    if request.method == "POST":
        utoken = request.form["utoken"]  # Get token from form
        user = User.query.filter_by(token=utoken).first()
        if user is None:
            flash("Could not reset password.")
            return redirect("/index")
        password = request.form["newpass"]
        repeat_pass = request.form["repeatnewpass"]
        if password != repeat_pass:
            error = "Passwords are not equal."
        elif not re.match(r"(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}", password):
            flash("Password could not be validated.")
            return redirect("/index")
        else:
            try:
                user.password_hash = security.generate_password_hash(
                    password
                )  # Create new hashed password
                user.token = None  # Remove token from database after confirmation
                db.session.commit()
                login_user(user)
            except IntegrityError as exc:
                db.session.rollback()
                flash("Could not reset password.")

            flash("Successfully reset password!")
            return redirect("/index")
    return render_template("reset_password.html", error=error, token=token)


## Events page routes
# Loads the Events page,
@app.route("/events")
def events():
    if current_user.is_authenticated:
        if current_user.is_confirmed == False:
            # If User is logged in but not verified, flash notice
            flash(
                Markup(
                    "You are not verified. Check your mail or resend the verification email in  <a href='"
                    + request.host_url
                    + "my_account'>settings</a>."
                )
            )

        # Get all non-cancelled upcoming and past Events, sorted latest first
        new_events = (
            Event.query.filter_by(is_cancelled=False)
            .filter(Event.date >= datetime.datetime.now())
            .order_by(desc(Event.date))
            .all()
        )
        past_events = (
            Event.query.filter_by(is_cancelled=False)
            .filter(Event.date <= datetime.datetime.now())
            .order_by(desc(Event.date))
            .all()
        )
        # Get all tickets currently booked
        total_booked_tickets = Ticket.query.filter_by(is_cancelled=False).all()
        # Get all cancelled Events, sorted latest first
        cancelled_events = (
            Event.query.filter_by(is_cancelled=True).order_by(desc(Event.date)).all()
        )
        # Get booked Tickets and Events that current User is booked for
        booked_tickets = (
            Ticket.query.filter_by(is_cancelled=False)
            .filter_by(user_id=current_user.id)
            .all()
        )
        booked_events = (
            Event.query.filter_by(is_cancelled=False)
            .filter(Event.id.in_(bt.event_id for bt in booked_tickets))
            .all()
        )

        return render_template(
            "events.html",
            new_events=new_events,
            past_events=past_events,
            cancelled_events=cancelled_events,
            booked_events=booked_events,
        )
    else:  # For non-logged in users
        new_events = (
            Event.query.filter_by(is_cancelled=False)
            .filter(Event.date >= datetime.datetime.now())
            .order_by(desc(Event.date))
            .all()
        )
        past_events = (
            Event.query.filter_by(is_cancelled=False)
            .filter(Event.date <= datetime.datetime.now())
            .order_by(desc(Event.date))
            .all()
        )
        total_booked_tickets = Ticket.query.filter_by(is_cancelled=False).all()
        cancelled_events = (
            Event.query.filter_by(is_cancelled=True).order_by(desc(Event.date)).all()
        )

        return render_template(
            "events.html",
            new_events=new_events,
            past_events=past_events,
            total_booked_tickets=total_booked_tickets,
            cancelled_events=cancelled_events,
        )


# Book a ticket/tickets for a User
@app.route("/book_ticket", methods=["GET", "POST"])
@login_required
def book_ticket():
    if request.method == "POST":
        event_id = request.form["eventid"]
        ticket_count = request.form["ticketcount"]
        event = Event.query.filter_by(id=event_id).first()
        organisers = User.query.filter_by(is_organiser=True)
        user_id = current_user.id
        created_at = datetime.datetime.now()
        is_cancelled = False
        try:
            for t in range(int(ticket_count)):  # Add each Ticket
                ticket = Ticket(
                    created_at=created_at,
                    is_cancelled=is_cancelled,
                    event_id=event_id,
                    user_id=user_id,
                )
                db.session.add(ticket)
                print("good")
                db.session.commit()
                print("commit")
                with open("static/barcodes/" + str(ticket.id) + ".svg", "wb") as f:
                    EAN13((f"{ticket.id:012}"), writer=SVGWriter()).write(
                        f
                    )  # Create Ticket barcode based on Ticket ID
            print("true")
            remaining_tickets = event.remaining - int(
                ticket_count
            )  # Remove Tickets from remaining space
            event.remaining = remaining_tickets
            db.session.commit()
            print("true2")
            if remaining_tickets < 0:
                flash("Could not request tickets.")
                return redirect("/events")

            # Check if event is nearly full
            if remaining_tickets < (event.capacity * 0.05):
                # Create announcement Notification
                message = (
                    "Announcement: "
                    + event.name
                    + " is almost full, with "
                    + str(remaining_tickets)
                    + " ticket(s) left."
                )
                if event.is_near_full == False:
                    event.is_near_full = True  # Only post Notification once per Organiser when Event is nearly full
                    for organiser in organisers:
                        db.session.add(
                            Notification(message, datetime.datetime.now(), organiser.id)
                        )
            else:
                event.is_near_full = False
            print("true3")
            # Check if Event is full
            if event.remaining == 0:
                # Create announcement Notification
                message = "Announcement: " + event.name + " is full."
                if event.is_full == False:
                    event.is_full = True  # Only post Notification once per Organiesr when Event is full
                    for organiser in organisers:
                        db.session.add(
                            Notification(message, datetime.datetime.now(), organiser.id)
                        )
            db.session.commit()
            # Set Event fields as required
            full(event)
            near_full(event)
            print("true4")
        except IntegrityError as exc:
            db.session.rollback()
            flash("Could not request ticket.")

        flash("Ticket successfully booked.")
        return redirect("/my_tickets")
    else:
        return render_template("my_tickets.html")


# Cancels all Tickets booked to an Event for a particular User
@app.route("/cancel_all_tickets", methods=["GET", "POST"])
@login_required
def cancel_all_tickets():
    if request.method == "POST":
        event_id = request.form["eventid"]
        event = Event.query.filter_by(id=event_id).first()
        # Get all non-cancelled Tickets linked to the Event owned by the current User
        owned_tickets = (
            Ticket.query.filter_by(user_id=current_user.id)
            .filter_by(is_cancelled=False)
            .filter_by(event_id=event_id)
            .all()
        )
        ticketcount = len(owned_tickets)

        try:
            for ticket in owned_tickets:
                ticket.is_cancelled = True  # Cancel each owned Ticket
            event.remaining += ticketcount  # Add tickets back to remaining space
            db.session.commit()
            # Set Event fields as required
            full(event)
            near_full(event)
        except IntegrityError as exc:
            db.session.rollback()
            flash("Could not cancel tickets.")

        flash("Tickets successfully cancelled.")
        return redirect("/my_tickets")
    else:
        return render_template("my_tickets.html")


# Set whether Event is full given Event capacity and remaining space
def full(event):
    if event.remaining == 0:  # If no more space, Event is full and not nearly full
        event.is_full = True
        event.is_near_full = False
    else:  # Otherwise, event is not full
        event.is_full = False
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        flash("Event could not be set to full.")


# Set whether Event is nearly full given Event capacity and remaining space
def near_full(event):
    if event.remaining < (
        event.capacity * 0.05
    ):  # If remaining space is less than 5% of Event capacity, Event is nearly full
        event.is_near_full = True
    else:  # If greater than or equal to 5%, Event is not nearly full
        event.is_near_full = False
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        flash("Event could not be set to nearly full.")


## Owned Tickets page routes
# Loads the owned Tickets page
@app.route("/my_tickets")
@login_required
def my_tickets():
    events = Event.query.all()
    # Get non-cancelled upcoming and past Events
    new_events = (
        Event.query.filter_by(is_cancelled=False)
        .filter(Event.date >= datetime.datetime.now())
        .all()
    )
    past_events = (
        Event.query.filter_by(is_cancelled=False)
        .filter(Event.date <= datetime.datetime.now())
        .all()
    )
    # Get non-cancelled Tickets for upcoming and past Events for the current User sorted in descending order by ID
    new_tickets = (
        Ticket.query.filter_by(is_cancelled=False)
        .filter(Ticket.event_id.in_([ne.id for ne in new_events]))
        .filter_by(user_id=current_user.id)
        .order_by(desc(Ticket.id))
        .all()
    )
    past_tickets = (
        Ticket.query.filter_by(is_cancelled=False)
        .filter(Ticket.event_id.in_([pe.id for pe in past_events]))
        .order_by(desc(Ticket.id))
        .filter_by(user_id=current_user.id)
        .all()
    )
    # Get cancelled
    cancelled_tickets = (
        Ticket.query.filter_by(user_id=current_user.id)
        .filter_by(is_cancelled=True)
        .order_by(desc(Ticket.id))
        .filter_by(user_id=current_user.id)
        .all()
    )

    return render_template(
        "my_tickets.html",
        events=events,
        new_tickets=new_tickets,
        past_tickets=past_tickets,
        cancelled_tickets=cancelled_tickets,
    )


# Cancels a single Ticket for an Attendee
@app.route("/cancel_ticket", methods=["GET", "POST"])
@login_required
def cancel_ticket():
    if request.method == "POST":
        # Get the ticket linked to the event
        event_id = request.form["eventid"]
        event = Event.query.filter_by(id=event_id).first()
        ticket = (
            Ticket.query.filter_by(user_id=current_user.id)
            .filter_by(is_cancelled=False)
            .filter_by(event_id=event_id)
            .first()
        )

        try:
            ticket.is_cancelled = True  # Set ticket as cancelled
            event.remaining += 1  # Add 1 to remaining events
            db.session.commit()
            full(event)
            near_full(event)
        except IntegrityError as exc:
            db.session.rollback()
            flash("Could not cancel ticket.")

        flash("Ticket successfully cancelled.")
        return redirect("/my_tickets")
    else:
        return render_template("my_tickets.html")


## Add Event page routes
# Add an Event as an Organiser
@app.route("/add_event", methods=["GET", "POST"])
@login_required
def add_event():
    if current_user.is_organiser == False:
        flash("You are not an organiser. Scram!")
        return redirect("/index")

    if current_user.is_confirmed == False:
        flash(
            Markup(
                "You are not verified. Check your mail or resend the verification email in  <a href='"
                + request.host_url
                + "my_account'>settings</a>."
            )
        )
        return redirect("/index")
    # Get all Users who are not current User
    users = User.query.filter(current_user.id != User.id).all()

    if request.method == "POST":
        name = request.form["name"]
        created_at = datetime.datetime.now()
        description = request.form["description"]
        date = datetime.datetime.strptime(
            request.form["date"], "%Y-%m-%dT%H:%M"
        )  # Parse date and time as a string
        # Set durations equal to 0 if one is not given an input
        if request.form["durationhours"] == "":
            duration_hrs = 1
        else:
            duration_hrs = int(request.form["durationhours"])
        if request.form["durationmins"] == "":
            duration_mins = 1
        else:
            duration_mins = int(request.form["durationmins"])

        capacity = request.form["capacity"]
        remaining = capacity  # Remaining space begins at capacity when Event is created
        location = request.form["location"]
        duration = (duration_hrs * 60) + duration_mins  # Total duration in minutes
        is_cancelled = False
        is_near_full = False
        is_full = False
        # Back-end validation
        if (
            name is None
            or len(name) <= 0
            or len(name) >= 500
            or date is None
            or date < datetime.datetime(1970, 1, 1)
            or date > datetime.datetime(2099, 12, 31, 23, 59)
            or len(description) >= 2001
            or request.form["durationhours"] == ""
            and request.form["durationmins"] == ""
            or duration_hrs <= 0
            or duration_hrs >= 10000
            or duration_mins <= 0
            or duration_mins >= 60
            or capacity is None
            or int(capacity) <= 4
            or int(capacity) >= 100000
            or location is None
            or len(location) <= 0
            or len(location) >= 1001
        ):
            flash("Invalid credentials.")
            return redirect("/index")

        image = ""
        image_file = request.files["image"]
        if image_file.filename == "":  # If no image given, use default image
            image = "defaultevent.jpg"

        if image_file and allowed_file(
            image_file.filename
        ):  # If image exists and validates
            filename = secure_filename(image_file.filename)
            unique_filename = make_unique(filename)  # Secure filename with unique value
            image_file.save(
                os.path.join(UPLOAD_FOLDER, "events", unique_filename)
            )  # Save image in upload folder
            image = unique_filename

        organiser_ids = request.form.getlist(
            "extraorgs"
        )  # Get IDs of checked Users to add as Organisers
        try:
            # Add Event and current User as an Organiser of the Event
            event = Event(
                name=name,
                created_at=created_at,
                date=date,
                description=description,
                duration=duration,
                capacity=capacity,
                remaining=remaining,
                location=location,
                image=image,
                is_cancelled=is_cancelled,
                is_near_full=is_near_full,
                is_full=is_full,
                creator_id=current_user.id,
            )
            db.session.add(event)
            db.session.commit()
            db.session.add(EventOrganiser(user_id=current_user.id, event_id=event.id))
            db.session.commit()
            # Add Event Organisers who were checked if any exist
            if organiser_ids is not None:
                for organiser_id in organiser_ids:
                    organiser = User.query.filter_by(id=organiser_id).first()
                    organiser.is_organiser = True
                    db.session.add(
                        EventOrganiser(user_id=organiser.id, event_id=event.id)
                    )
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            flash("Could not add event.")

        flash("Event added.")
        return redirect("/my_events")
    else:
        return render_template("add_event.html", users=users)


## Owned Events page routes
# Loads events that an Organiser is an owner of
@app.route("/my_events")
@login_required
def my_events():
    if current_user.is_organiser == False:
        flash("You are not an organiser. Scram!")
        return redirect("/index")

    orgevents = EventOrganiser.query.filter_by(user_id=current_user.id).all()
    events = (
        Event.query.filter(Event.id.in_([e.event_id for e in orgevents]))
        .order_by(Event.created_at.desc())
        .all()
    )

    return render_template("my_events.html", events=events)


# Loads the form to edit the Event
@app.route("/load_manage_event", methods=["GET", "POST"])
@login_required
def load_manage_event():
    event_id = request.form["eventid"]
    event = Event.query.filter_by(id=event_id).first()
    booked_tickets = (
        Ticket.query.filter_by(is_cancelled=False).filter_by(event_id=event_id).count()
    )
    # Get creator of Event
    event_creator = User.query.filter_by(id=event.creator_id).first()
    # Get all Event organisers
    event_organiser_ids = EventOrganiser.query.filter_by(event_id=event_id).all()
    event_organisers = (
        User.query.filter_by(is_organiser=True)
        .filter(User.id != event_creator.id)
        .filter(User.id.in_([e.user_id for e in event_organiser_ids]))
        .all()
    )
    # Get all Users who are not Event Organisers
    non_event_organisers = User.query.filter(
        User.id.notin_([e.user_id for e in event_organiser_ids])
    ).all()

    return render_template(
        "manage_event.html",
        event=event,
        booked_tickets=booked_tickets,
        event_creator=event_creator,
        event_organisers=event_organisers,
        non_event_organisers=non_event_organisers,
    )


# Allows an Event's information to be changed, excluding date and time
@app.route("/manage_event", methods=["GET", "POST"])
@login_required
def manage_event():
    if current_user.is_organiser == False:
        flash("You are not an organiser. Scram!")
        return redirect("/index")

    if request.method == "POST":
        event_id = request.form["eventid"]
        event = Event.query.filter_by(id=event_id).first()
        booked_tickets = (
            Ticket.query.filter_by(is_cancelled=False)
            .filter_by(event_id=event_id)
            .count()
        )
        name = request.form["name"]
        description = request.form["description"]
        # Set durations equal to 0 if one is not given an input
        if request.form["durationhours"] == "":
            duration_hrs = 1
        else:
            duration_hrs = int(request.form["durationhours"])
        if request.form["durationmins"] == "":
            duration_mins = 1
        else:
            duration_mins = int(request.form["durationmins"])

        capacity = request.form["capacity"]
        location = request.form["location"]
        duration = (duration_hrs * 60) + duration_mins  # Total duration in minutes
        image_file = request.files["image"]
        organiser_ids = request.form.getlist("extraorgs")
        # Back-end validation
        if (
            name is None
            or len(name) <= 0
            or len(name) >= 500
            or len(description) >= 2001
            or request.form["durationhours"] == ""
            and request.form["durationmins"] == ""
            or duration_hrs <= 0
            or duration_hrs >= 10000
            or duration_mins <= 0
            or duration_mins >= 60
            or capacity is None
            or int(capacity) < 5
            or int(capacity) < (event.capacity - event.remaining)
            or int(capacity) >= 100000
            or location is None
            or len(location) <= 0
            or len(location) >= 1001
        ):
            flash("Invalid credentials.")
            return redirect("/index")

        # If any information has changed, update it
        try:
            if name != event.name:
                event.name = name

            if description != event.description:
                event.description = description

            if duration != event.duration:
                event.duration = duration

            if capacity != event.capacity:
                event.capacity = capacity

            if location != event.location:
                event.location = location

            if image_file.filename != event.image:
                # Image validation
                if image_file == "":
                    event.image = "defaultevent.jpg"

                if image_file and allowed_file(image_file.filename):
                    filename = secure_filename(image_file.filename)
                    unique_filename = make_unique(
                        filename
                    )  # Secure filename with unique value
                    image_file.save(
                        os.path.join(UPLOAD_FOLDER, "events", unique_filename)
                    )
                    event.image = unique_filename
            # If Users were selected, add them as Event Organisers
            if organiser_ids is not None:
                for organiser_id in organiser_ids:
                    organiser = User.query.filter_by(id=organiser_id).first()
                    organiser.is_organiser = True
                    db.session.add(
                        EventOrganiser(user_id=organiser.id, event_id=event.id)
                    )

            db.session.commit()
            event.remaining = event.capacity - booked_tickets
            db.session.commit()
            full(event)
            near_full(event)
        except IntegrityError as exc:
            db.session.rollback()
            flash("Could not update list.")

        flash("Event updated.")
        return redirect("/my_events")
    else:
        return render_template("manage_event.html")


# Cancel an Event as an Organiser assigned as an owner of the Event
@app.route("/cancel_event", methods=["GET", "POST"])
@login_required
def cancel_event():
    if current_user.is_organiser == False:
        flash("You are not an organiser. Scram!")
        return redirect("/index")

    if request.method == "POST":
        description = request.form["description"]
        event_id = request.form["eventid"]
        event = Event.query.filter_by(id=event_id).one()
        tickets = Ticket.query.filter_by(is_cancelled=False).filter_by(
            event_id=event.id
        )
        # Get booked Users and Organisers
        booked_users = User.query.filter(
            User.id.in_([t.user_id for t in tickets])
        ).all()
        organisers = (
            User.query.filter_by(is_organiser=True)
            .filter(User.id.notin_([bu.id for bu in booked_users]))
            .all()
        )
        try:
            event.is_cancelled = True
            for ticket in tickets:
                ticket.is_cancelled = True
            # Create announcement Notification
            message = (
                "Announcement: "
                + event.name
                + " has been cancelled. Reason: "
                + description
            )
            # Send Notification to each booked User and Organiser
            for user in booked_users:
                db.session.add(Notification(message, datetime.datetime.now(), user.id))
            for organiser in organisers:
                db.session.add(
                    Notification(message, datetime.datetime.now(), organiser.id)
                )

            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            flash("Could not cancel event.")

        flash("Event successfully cancelled.")
        return redirect("/my_events")
    else:
        return render_template("my_events.html")


## Notification page routes
# Loads Notification page
@app.route("/notifications")
@login_required
def notifications():
    current_user.last_message_read_time = (
        datetime.datetime.now()
    )  # Refresh the time page was last read by User
    db.session.commit()
    notifs = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(desc(Notification.date))
        .all()
    )

    return render_template("notifications.html", notifs=notifs)


# Deletes a particular Notification asynchronously
@app.route("/delete_notif", methods=["GET", "POST"])
@login_required
def delete_notif():
    if request.method == "POST":
        notif_id = request.json["notifid"]
        notif = Notification.query.filter_by(
            id=notif_id
        ).one()  # Get the Notification linked to the ID
        try:
            db.session.delete(notif)  # Delete the Notification
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            flash("Notification could not be deleted.")
    flash("Notification successfully deleted.")
    return render_template("notifications.html")


## Account page routes
@app.route("/my_account")
@login_required
def my_account():
    return render_template("my_account.html")


# Uploads a picture provided by the User as their profile picture
@app.route("/upload_avatar", methods=["GET", "POST"])
@login_required
def upload_avatar():
    if request.method == "POST":
        if "avatar" not in request.files:  # If no file part, redirect
            flash("No file part")
            return redirect("/my_account")
        image = request.files["avatar"]
        if image.filename == "":
            flash("No selected file")  # If no file selected, redirect
            return redirect("/my_account")
        if image and allowed_file(
            image.filename
        ):  # If image exists and validated, save it
            filename = secure_filename(image.filename)
            unique_filename = make_unique(filename)  # Secure filename with unique value
            image.save(
                os.path.join(UPLOAD_FOLDER, "avatars/", unique_filename)
            )  # Save in given folder
            avatar = unique_filename

            try:
                current_user.avatar = avatar
                db.session.commit()
            except IntegrityError as exc:
                db.session.rollback()
                flash("Could not update profile picture.")
        flash("Profile picture updated.")
        return redirect("/my_account")
    else:
        return render_template("my_account.html")


# Creates a UUID value to prepend to image filename
def make_unique(string):
    unique = uuid.uuid4().__str__()
    return f"{unique}-{string}"


# Validates a given image by checking its extension
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Resends verification email by clicking link on Account page
@app.route("/resend_verify_email", methods=["GET", "POST"])
@login_required
def resend_verify_email():
    if current_user.is_confirmed:
        flash("Already verified.")
        return redirect("/index")

    try:
        current_user.token = uuid.uuid4().hex  # Set User token as a UUID string
        db.session.commit()
        msg = Message(
            subject="Verify your GigUp account",
            sender=("GigUp", "gigup-admin@example.com"),
            recipients=[current_user.email],
        )
        msg.html = render_template("verify_message.html")
        # Attach an image to the header
        msg.attach(
            "gigup-logo-mail.png",
            "image/png",
            open(
                os.path.join(UPLOAD_FOLDER, "images", "gigup-logo-mail.png"), "rb"
            ).read(),
            "inline",
            headers=[["Content-ID", "<MyImage>"]],
        )
        assert msg.sender == "GigUp <gigup-admin@example.com>"
        mail.send(msg)
    except IntegrityError as exc:
        db.session.rollback()
        flash("Verification email could not be sent.")

    flash("Verification email sent. Check your mail to verify your account.")
    return render_template("my_account.html")


# Updates the User's username
@app.route("/update_name", methods=["GET", "POST"])
@login_required
def update_name():
    if request.method == "POST":
        uname = request.form["username"]
        # Back-end validation
        if len(uname) <= 2 or len(uname) >= 21:
            flash("Username could not be validated.")
            return redirect("/my_account")
        if uname == "":
            flash("No username specified.")
            return redirect("/my_account")
        if uname == current_user.username:
            flash("Username is not new.")
            return redirect("/my_account")
        try:
            user = User.query.get(current_user.id)
            user.username = uname
            db.session.add(user)
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            flash("Could not update name.")

        flash("Username changed successfully.")
        return redirect("/my_account")

    else:
        return render_template("my_account.html")


# Logs out the User
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have successfully logged yourself out.")
    return redirect("/")


# Deletes the User's account
@app.route("/delete_user")
@login_required
def delete_user():
    user = User.query.filter_by(id=current_user.id).one()
    user_id = current_user.id
    logout_user()
    organiser_id = EventOrganiser.query.filter_by(user_id=user_id)
    for org in organiser_id:
        db.session.delete(org)
    db.session.delete(user)
    db.session.commit()
    flash("You have successfully deleted your account.")
    return redirect("/index")


## Footer page routes
# About page
@app.route("/about")
def about():
    return render_template("about.html")


# Credits page
@app.route("/credits")
def credits():
    return render_template("credits.html")
