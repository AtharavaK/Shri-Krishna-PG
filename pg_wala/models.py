from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ── Owner account (Flask-Login user) ──────────────────────────────────────────
class Owner(UserMixin, db.Model):
    __tablename__ = 'owners'
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    # Flask-Login requires get_id() to return a string prefixed so we can
    # distinguish owner vs guest sessions
    def get_id(self):
        return f'owner-{self.id}'

# ── Room & Bed ─────────────────────────────────────────────────────────────────
class Room(db.Model):
    __tablename__ = 'rooms'
    room_no   = db.Column(db.Integer, primary_key=True)
    room_type = db.Column(db.String(10), default='Non-AC')
    capacity  = db.Column(db.Integer, default=2)
    floor     = db.Column(db.Integer, default=0)
    beds      = db.relationship('Bed', backref='room', lazy=True, cascade='all, delete-orphan')

class Bed(db.Model):
    __tablename__ = 'beds'
    bed_id      = db.Column(db.Integer, primary_key=True)
    room_no     = db.Column(db.Integer, db.ForeignKey('rooms.room_no'), nullable=False)
    is_occupied = db.Column(db.Boolean, default=False)
    guest       = db.relationship('Guest', backref='bed', uselist=False)

# ── Guest ──────────────────────────────────────────────────────────────────────
class Guest(db.Model):
    __tablename__ = 'guests'
    guest_id     = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.String(20))
    id_proof     = db.Column(db.String(100))
    bed_id       = db.Column(db.Integer, db.ForeignKey('beds.bed_id'), nullable=True)
    joined_on    = db.Column(db.DateTime, default=datetime.utcnow)
    is_active    = db.Column(db.Boolean, default=True)
    checkout_requested = db.Column(db.Boolean, default=False)
    complaints   = db.relationship('Complaint', backref='guest', lazy=True)

    # Flask-Login support for guests
    def get_id(self):
        return f'guest-{self.guest_id}'

    @property
    def is_authenticated(self): return True
    @property
    def is_active_user(self):   return self.is_active
    @property
    def is_anonymous(self):     return False

# ── Complaint ──────────────────────────────────────────────────────────────────
class Complaint(db.Model):
    __tablename__ = 'complaints'
    complaint_id = db.Column(db.Integer, primary_key=True)
    description  = db.Column(db.Text, nullable=False)
    status       = db.Column(db.String(20), default='New')
    date_logged  = db.Column(db.DateTime, default=datetime.utcnow)
    guest_id     = db.Column(db.Integer, db.ForeignKey('guests.guest_id'), nullable=True)

# ── Notice board (shared) ──────────────────────────────────────────────────────
class Notice(db.Model):
    __tablename__ = 'notices'
    notice_id   = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(150), nullable=False)
    body        = db.Column(db.Text, nullable=False)
    posted_on   = db.Column(db.DateTime, default=datetime.utcnow)
    is_pinned   = db.Column(db.Boolean, default=False)
