"""Script to create a super admin user"""
from app import create_app
from app.models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Check if user already exists
    existing = User.query.filter_by(email='oumou_admin@gmail.com').first()
    if existing:
        print("! User already exists, updating password...")
        existing.password_hash = generate_password_hash('123')
        existing.is_active = True
        db.session.commit()
        print("✓ Password updated!")
    else:
        # Create new super admin
        admin = User(
            email='oumou_admin@gmail.com',
            first_name='Oumou',
            last_name='Admin',
            role='admin',
            is_active=True
        )
        admin.password_hash = generate_password_hash('123')
        db.session.add(admin)
        db.session.commit()
        print("✓ Super Admin created!")
    
    print("\n  Email: oumou_admin@gmail.com")
    print("  Password: 123")
    print("  Role: Super Admin")
