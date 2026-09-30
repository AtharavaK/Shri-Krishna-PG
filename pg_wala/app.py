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

# ── Flask-Login ──────────────────────────────────────────────────────────
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

# ── Blueprints ──────────────────────────────────────────────────────────
from routes.auth  import auth_bp
from routes.owner import owner_bp
from routes.guest import guest_bp

app.register_blueprint(auth_bp)
app.register_blueprint(owner_bp, url_prefix='/owner')
app.register_blueprint(guest_bp, url_prefix='/guest')

# ── DB init ────────────────────────────────────────────────────────────
# NOTE: Default owner creation moved to environment variable for security
with app.app_context():
    db.create_all()
    # Only create default owner if explicitly enabled via environment variable
    if os.environ.get('CREATE_DEFAULT_OWNER', 'false').lower() == 'true':
        if not Owner.query.first():
            default_username = os.environ.get('DEFAULT_OWNER_USERNAME', 'owner')
            default_password = os.environ.get('DEFAULT_OWNER_PASSWORD')
            if default_password:
                o = Owner(username=default_username)
                o.set_password(default_password)
                db.session.add(o)
                db.session.commit()
                print(f"✅ Default owner created → username: {default_username}")
            else:
                print("⚠️  CREATE_DEFAULT_OWNER is enabled but DEFAULT_OWNER_PASSWORD is not set")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

