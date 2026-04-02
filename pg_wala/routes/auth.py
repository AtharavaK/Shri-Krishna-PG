from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from models import db, Owner, Guest

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if isinstance(current_user, Owner):
            return redirect(url_for('owner.dashboard'))
        return redirect(url_for('guest.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        role = request.form.get('role')

        if role == 'owner':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            owner = Owner.query.filter_by(username=username).first()
            if owner and owner.check_password(password):
                login_user(owner)
                return redirect(url_for('owner.dashboard'))
            flash('Invalid owner credentials.', 'error')

        elif role == 'guest':
            name     = request.form.get('name', '').strip().lower()
            id_proof = request.form.get('id_proof', '').strip()
            guest = Guest.query.filter(
                db.func.lower(Guest.name) == name,
                Guest.id_proof == id_proof,
                Guest.is_active == True
            ).first()
            if guest:
                login_user(guest)
                return redirect(url_for('guest.dashboard'))
            flash('No active guest found with those details.', 'error')

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
