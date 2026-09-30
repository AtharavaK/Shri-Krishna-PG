from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import db, Guest, Complaint, Room, Bed, Notice, Owner

owner_bp = Blueprint('owner', __name__)

def owner_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not isinstance(current_user, Owner):
            flash('Owner access only.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

# ── Dashboard ───────────────────────────────────────────────────────────
@owner_bp.route('/')
@owner_required
def dashboard():
    total_guests      = Guest.query.filter_by(is_active=True).count()
    total_beds        = Bed.query.count()
    occupied_beds     = Bed.query.filter_by(is_occupied=True).count()
    open_complaints   = Complaint.query.filter(Complaint.status != 'Resolved').count()
    checkout_requests = Guest.query.filter_by(is_active=True, checkout_requested=True).count()
    recent_complaints = Complaint.query.order_by(Complaint.date_logged.desc()).limit(5).all()
    recent_guests     = Guest.query.filter_by(is_active=True).order_by(Guest.joined_on.desc()).limit(5).all()
    return render_template('owner/dashboard.html',
        total_guests=total_guests, total_beds=total_beds,
        occupied_beds=occupied_beds, vacant_beds=total_beds - occupied_beds,
        open_complaints=open_complaints, checkout_requests=checkout_requests,
        recent_complaints=recent_complaints, recent_guests=recent_guests)

# ── Guests ────────────────────────────────────────────────────────────
@owner_bp.route('/guests', methods=['GET', 'POST'])
@owner_required
def guests():
    if request.method == 'POST':
        # Validate required fields
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact', '').strip()
        id_proof = request.form.get('id_proof', '').strip()
        bed_id = request.form.get('bed_id') or None

        if not name or not contact or not id_proof:
            flash('All fields (name, contact, ID proof) are required.', 'error')
            all_guests = Guest.query.filter_by(is_active=True).order_by(Guest.joined_on.desc()).all()
            vacant_beds = Bed.query.filter_by(is_occupied=False).all()
            checkouts = Guest.query.filter_by(is_active=True, checkout_requested=True).all()
            return render_template('owner/guests.html',
                guests=all_guests, vacant_beds=vacant_beds, checkouts=checkouts)

        try:
            g = Guest(
                name=name,
                contact_info=contact,
                id_proof=id_proof,
                bed_id=int(bed_id) if bed_id else None
            )
            db.session.add(g)
            if bed_id:
                bed = Bed.query.get(int(bed_id))
                if bed:
                    bed.is_occupied = True
            db.session.commit()
            flash(f'Guest "{g.name}" registered successfully.', 'success')
        except (ValueError, Exception) as e:
            db.session.rollback()
            flash(f'Error registering guest: {str(e)}', 'error')
        return redirect(url_for('owner.guests'))

    all_guests   = Guest.query.filter_by(is_active=True).order_by(Guest.joined_on.desc()).all()
    vacant_beds  = Bed.query.filter_by(is_occupied=False).all()
    checkouts    = Guest.query.filter_by(is_active=True, checkout_requested=True).all()
    return render_template('owner/guests.html',
        guests=all_guests, vacant_beds=vacant_beds, checkouts=checkouts)

@owner_bp.route('/guests/edit/<int:gid>', methods=['GET', 'POST'])
@owner_required
def edit_guest(gid):
    g = Guest.query.get_or_404(gid)
    if request.method == 'POST':
        # Validate required fields
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact', '').strip()
        id_proof = request.form.get('id_proof', '').strip()

        if not name or not contact or not id_proof:
            flash('All fields are required.', 'error')
            return render_template('owner/edit_guest.html', guest=g)

        try:
            g.name         = name
            g.contact_info = contact
            g.id_proof     = id_proof
            db.session.commit()
            flash('Guest updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating guest: {str(e)}', 'error')
            return render_template('owner/edit_guest.html', guest=g)
        return redirect(url_for('owner.guests'))
    return render_template('owner/edit_guest.html', guest=g)

@owner_bp.route('/guests/checkout/<int:gid>', methods=['POST'])
@owner_required
def checkout_guest(gid):
    g = Guest.query.get_or_404(gid)
    if g.bed_id:
        bed = Bed.query.get(g.bed_id)
        if bed:
            bed.is_occupied = False
    g.is_active = False
    g.checkout_requested = False
    db.session.commit()
    flash(f'{g.name} checked out.', 'info')
    return redirect(url_for('owner.guests'))

@owner_bp.route('/guests/dismiss-checkout/<int:gid>', methods=['POST'])
@owner_required
def dismiss_checkout(gid):
    g = Guest.query.get_or_404(gid)
    g.checkout_requested = False
    db.session.commit()
    flash('Checkout request dismissed.', 'info')
    return redirect(url_for('owner.guests'))

# ── Complaints ──────────────────────────────────────────────────────────
@owner_bp.route('/complaints', methods=['GET', 'POST'])
@owner_required
def complaints():
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        guest_id = request.form.get('guest_id') or None

        if not description:
            flash('Description is required.', 'error')
            sf = request.args.get('status', 'all')
            q = Complaint.query
            if sf != 'all':
                q = q.filter_by(status=sf)
            complaints_list = q.order_by(Complaint.date_logged.desc()).all()
            active_guests = Guest.query.filter_by(is_active=True).all()
            return render_template('owner/complaints.html',
                complaints=complaints_list, status_filter=sf, active_guests=active_guests)

        try:
            c = Complaint(
                description=description,
                guest_id=int(guest_id) if guest_id else None
            )
            db.session.add(c)
            db.session.commit()
            flash('Complaint filed successfully.', 'success')
        except (ValueError, Exception) as e:
            db.session.rollback()
            flash(f'Error filing complaint: {str(e)}', 'error')
        return redirect(url_for('owner.complaints'))

    sf = request.args.get('status', 'all')
    q  = Complaint.query
    if sf != 'all':
        q = q.filter_by(status=sf)
    complaints_list    = q.order_by(Complaint.date_logged.desc()).all()
    active_guests = Guest.query.filter_by(is_active=True).all()
    return render_template('owner/complaints.html',
        complaints=complaints_list, status_filter=sf, active_guests=active_guests)

@owner_bp.route('/complaints/update/<int:cid>', methods=['POST'])
@owner_required
def update_complaint(cid):
    c = Complaint.query.get_or_404(cid)
    status = request.form.get('status', '').strip()
    
    if not status:
        flash('Status is required.', 'error')
        return redirect(url_for('owner.complaints'))
    
    try:
        c.status = status
        db.session.commit()
        flash('Status updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
    return redirect(url_for('owner.complaints'))

@owner_bp.route('/complaints/delete/<int:cid>', methods=['POST'])
@owner_required
def delete_complaint(cid):
    c = Complaint.query.get_or_404(cid)
    try:
        db.session.delete(c)
        db.session.commit()
        flash('Complaint removed.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting complaint: {str(e)}', 'error')
    return redirect(url_for('owner.complaints'))

# ── Rooms ────────────────────────────────────────────────────────────
@owner_bp.route('/rooms', methods=['GET', 'POST'])
@owner_required
def rooms():
    if request.method == 'POST':
        # Validate required fields
        room_no = request.form.get('room_no', '').strip()
        room_type = request.form.get('room_type', '').strip()
        capacity = request.form.get('capacity', '').strip()
        floor = request.form.get('floor', '').strip()

        if not room_no or not room_type or not capacity or not floor is None:
            flash('All fields are required.', 'error')
            rooms_list = Room.query.order_by(Room.floor, Room.room_no).all()
            return render_template('owner/rooms.html', rooms=rooms_list)

        try:
            room = Room(
                room_no=int(room_no),
                room_type=room_type,
                capacity=int(capacity),
                floor=int(floor)
            )
            db.session.add(room)
            db.session.flush()
            for _ in range(room.capacity):
                db.session.add(Bed(room_no=room.room_no))
            db.session.commit()
            flash(f'Room {room.room_no} added successfully.', 'success')
        except (ValueError, Exception) as e:
            db.session.rollback()
            flash(f'Error adding room: {str(e)}', 'error')
        return redirect(url_for('owner.rooms'))

    rooms_list = Room.query.order_by(Room.floor, Room.room_no).all()
    return render_template('owner/rooms.html', rooms=rooms_list)

@owner_bp.route('/rooms/delete/<int:rno>', methods=['POST'])
@owner_required
def delete_room(rno):
    r = Room.query.get_or_404(rno)
    try:
        db.session.delete(r)
        db.session.commit()
        flash('Room deleted.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting room: {str(e)}', 'error')
    return redirect(url_for('owner.rooms'))

# ── Notices ──────────────────────────────────────────────────────────
@owner_bp.route('/notices', methods=['GET', 'POST'])
@owner_required
def notices():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()

        if not title or not body:
            flash('Title and body are required.', 'error')
            notices_list = Notice.query.order_by(Notice.is_pinned.desc(), Notice.posted_on.desc()).all()
            return render_template('owner/notices.html', notices=notices_list)

        try:
            n = Notice(
                title=title,
                body=body,
                is_pinned='is_pinned' in request.form
            )
            db.session.add(n)
            db.session.commit()
            flash('Notice posted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error posting notice: {str(e)}', 'error')
        return redirect(url_for('owner.notices'))

    notices_list = Notice.query.order_by(Notice.is_pinned.desc(), Notice.posted_on.desc()).all()
    return render_template('owner/notices.html', notices=notices_list)

@owner_bp.route('/notices/delete/<int:nid>', methods=['POST'])
@owner_required
def delete_notice(nid):
    n = Notice.query.get_or_404(nid)
    try:
        db.session.delete(n)
        db.session.commit()
        flash('Notice deleted.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting notice: {str(e)}', 'error')
    return redirect(url_for('owner.notices'))

# ── Settings (change username/password) ───────────────────────────────────────
@owner_bp.route('/settings', methods=['GET', 'POST'])
@owner_required
def settings():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()

        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('owner.settings'))

        new_username     = request.form.get('new_username', '').strip()
        new_password     = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if new_username:
            existing = Owner.query.filter_by(username=new_username).first()
            if existing and existing.id != current_user.id:
                flash('That username is already taken.', 'error')
                return redirect(url_for('owner.settings'))
            current_user.username = new_username

        if new_password:
            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                return redirect(url_for('owner.settings'))
            if len(new_password) < 6:
                flash('Password must be at least 6 characters.', 'error')
                return redirect(url_for('owner.settings'))
            current_user.set_password(new_password)

        try:
            db.session.commit()
            flash('Credentials updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating credentials: {str(e)}', 'error')
        return redirect(url_for('owner.settings'))

    return render_template('owner/settings.html')
