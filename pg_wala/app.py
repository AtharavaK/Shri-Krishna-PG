import os
from flask import Flask
from flask_login import LoginManager
from models import db, Owner, Guest

app = Flask(__name__)

# Use DATABASE_URL from environment (Render PostgreSQL),
# fall back to local SQLite for development
database_url = os.environ.get('DATABASE_URL', 'sqlite:///pg_wala.db')

# Render gives postgres:// but SQLAlchemy needs postgresql://
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'pgwala-super-secret-2025')

db.init_app(app)

# ── Flask-Login ────────────────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to continue.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith('owner-'):
        return Owner.query.get(int(user_id.split('-')[1]))
    elif user_id.startswith('guest-'):
        return Guest.query.get(int(user_id.split('-')[1]))
    return None

# ── Blueprints ─────────────────────────────────────────────────────────────────
from routes.auth  import auth_bp
from routes.owner import owner_bp
from routes.guest import guest_bp

app.register_blueprint(auth_bp)
app.register_blueprint(owner_bp, url_prefix='/owner')
app.register_blueprint(guest_bp, url_prefix='/guest')

# ── DB init + default owner ────────────────────────────────────────────────────
with app.app_context():
    db.create_all()
    if not Owner.query.first():
        o = Owner(username='owner')
        o.set_password('admin123')
        db.session.add(o)
        db.session.commit()
        print("✅ Default owner created → username: owner | password: admin123")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


