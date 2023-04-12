import datetime

from flask import Flask
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug import security

# Create the database interface
db = SQLAlchemy()


# A model of a User all other Users will inherit from
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(25), nullable=False)
    is_organiser = db.Column(db.Boolean, nullable=False, default=False)
    is_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    avatar = db.Column(db.String, nullable=True)
    token = db.Column(db.String(32), nullable=True)
    last_message_read_time = db.Column(
        db.DateTime, nullable=False, default=datetime.datetime.now()
    )
    events = db.relationship("Event", backref="users", lazy=True, cascade="all, delete")
    tickets = db.relationship(
        "Ticket", backref="users", lazy=True, cascade="all, delete"
    )

    def __init__(
        self, username, email, password_hash, is_organiser, is_confirmed, avatar, token
    ):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_organiser = is_organiser
        self.is_confirmed = is_confirmed
        self.avatar = avatar
        self.token = token

    # Returns the number of new unread notifications for a particular User
    def new_notifs(self):
        last_read_time = self.last_message_read_time
        # Return number of notifications that are posted after User last refreshed Notifications page
        return (
            Notification.query.filter_by(user_id=self.id)
            .filter(Notification.date >= last_read_time)
            .count()
        )


# A model of an Event that can be created by Users who are Organisers
class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime)
    date = db.Column(db.DateTime)
    description = db.Column(db.String(2000))
    duration = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    remaining = db.Column(db.Integer, nullable=False, default=capacity)
    location = db.Column(db.String(1000), nullable=False)
    image = db.Column(db.String(300), nullable=True)
    is_cancelled = db.Column(db.Boolean, nullable=False, default=False)
    is_near_full = db.Column(db.Boolean, nullable=False, default=False)
    is_full = db.Column(db.Boolean, nullable=False, default=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    tickets = db.relationship(
        "Ticket", backref="events", lazy=True, cascade="all, delete"
    )

    def __init__(
        self,
        name,
        created_at,
        date,
        description,
        duration,
        capacity,
        remaining,
        location,
        image,
        is_cancelled,
        is_near_full,
        is_full,
        creator_id,
    ):
        self.name = name
        self.created_at = created_at
        self.date = date
        self.description = description
        self.duration = duration
        self.capacity = capacity
        self.remaining = remaining
        self.location = location
        self.image = image
        self.is_cancelled = is_cancelled
        self.is_near_full = is_near_full
        self.is_full = is_full
        self.creator_id = creator_id


# A model that links Events with their owners, who are Users assigned as an Organiser
class EventOrganiser(db.Model):
    __tablename__ = "eventorganisers"
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, primary_key=True
    )
    event_id = db.Column(
        db.Integer, db.ForeignKey("events.id"), nullable=False, primary_key=True
    )

    def __init__(self, user_id, event_id):
        self.user_id = user_id
        self.event_id = event_id


# A model for a Ticket linked to an Event that can be booked by a User
class Ticket(db.Model):
    __tablename__ = "tickets"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime)
    is_cancelled = db.Column(db.Boolean, nullable=False, default=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __init__(self, created_at, is_cancelled, event_id, user_id):
        self.created_at = created_at
        self.is_cancelled = is_cancelled
        self.event_id = event_id
        self.user_id = user_id


# A model for a Notification message that is sent to a particular User
class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(2000))
    date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __init__(self, message, date, user_id):
        self.message = message
        self.date = date
        self.user_id = user_id


# Insert some data into the tables
def dbinit():
    user_list = [
        User(
            "Mike",
            "mike@example.com",
            security.generate_password_hash("Stickman1!"),
            True,
            True,
            "2cc607a4-95e4-4da7-91aa-c011252da596-defaultavatar.png",
            None,
        ),
        User(
            "Dmitry",
            "dmitry@example.com",
            security.generate_password_hash("Stickman1!"),
            True,
            True,
            "2cc607a4-95e4-4da7-91aa-c011252da596-defaultavatar.png",
            None,
        ),
        User(
            "Bill",
            "bill@example.com",
            security.generate_password_hash("Stickman1!"),
            False,
            True,
            "2cc607a4-95e4-4da7-91aa-c011252da596-defaultavatar.png",
            None,
        ),
    ]
    db.session.add_all(user_list)

    # Commit all the changes to the database file
    db.session.commit()
