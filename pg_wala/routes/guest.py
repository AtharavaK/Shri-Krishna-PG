from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from models import db, Complaint, Notice, Guest

guest_bp = Blueprint('guest', __name__)

def guest_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not isinstance(current_user, Guest):
            flash('Guest access only.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

# ── Dashboard ──────────────────────────────────────────────────────────────────
@guest_bp.route('/')
@guest_required
def dashboard():
    my_complaints = Complaint.query.filter_by(
        guest_id=current_user.guest_id
    ).order_by(Complaint.date_logged.desc()).limit(3).all()

    notices = Notice.query.order_by(
        Notice.is_pinned.desc(), Notice.posted_on.desc()
    ).limit(5).all()

    return render_template('guest/dashboard.html',
        guest=current_user,
        my_complaints=my_complaints,
        notices=notices)

# ── Profile ────────────────────────────────────────────────────────────────────
@guest_bp.route('/profile')
@guest_required
def profile():
    return render_template('guest/profile.html', guest=current_user)

# ── Complaints ─────────────────────────────────────────────────────────────────
@guest_bp.route('/complaints', methods=['GET', 'POST'])
@guest_required
def complaints():
    if request.method == 'POST':
        desc = request.form.get('description', '').strip()
        if desc:
            c = Complaint(description=desc, guest_id=current_user.guest_id)
            db.session.add(c); db.session.commit()
            flash('Complaint submitted. We will look into it!', 'success')
        return redirect(url_for('guest.complaints'))

    my_complaints = Complaint.query.filter_by(
        guest_id=current_user.guest_id
    ).order_by(Complaint.date_logged.desc()).all()
    return render_template('guest/complaints.html',
        complaints=my_complaints, guest=current_user)

# ── Notices (read-only) ────────────────────────────────────────────────────────
@guest_bp.route('/notices')
@guest_required
def notices():
    notices = Notice.query.order_by(
        Notice.is_pinned.desc(), Notice.posted_on.desc()
    ).all()
    return render_template('guest/notices.html', notices=notices, guest=current_user)

# ── Request Checkout ───────────────────────────────────────────────────────────
@guest_bp.route('/request-checkout', methods=['POST'])
@guest_required
def request_checkout():
    if current_user.checkout_requested:
        flash('You have already requested checkout. The owner will process it soon.', 'info')
    else:
        current_user.checkout_requested = True
        db.session.commit()
        flash('Checkout requested! The owner will process it shortly.', 'success')
    return redirect(url_for('guest.dashboard'))
