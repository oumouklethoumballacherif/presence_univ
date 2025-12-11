from app import create_app
from app.models import User
import datetime

app = create_app()

with app.app_context():
    student = User.query.filter_by(role='student').order_by(User.created_at.desc()).first()
    if student:
        print(f"Student: {student.first_name} {student.last_name}")
        print(f"Email: {student.email}")
        print(f"Token: {student.token}")
        print(f"Expiry (UTC): {student.token_expiry}")
        print(f"Current UTC: {datetime.datetime.utcnow()}")
        
        if student.token and student.token_expiry:
             is_valid = datetime.datetime.utcnow() < student.token_expiry
             print(f"Token Valid? {is_valid}")
        else:
            print("Token or Expiry missing")
            
        # Also print the last 5 students to see if any have tokens
        print("\nLast 5 students:")
        students = User.query.filter_by(role='student').order_by(User.created_at.desc()).limit(5).all()
        for s in students:
             print(f"- {s.email}: Token={s.token is not None}, Expiry={s.token_expiry}")

    else:
        print("No students found.")
