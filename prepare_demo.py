from app import create_app, db
from app.models import User, Track, Department, AcademicYear
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Ensure a department exists
    dept = Department.query.filter_by(name="Informatique").first()
    if not dept:
        dept = Department(name="Informatique", description="Dept Info")
        db.session.add(dept)
        db.session.commit()
    
    # Ensure a track exists
    track = Track.query.filter_by(code="GI").first()
    if not track:
        track = Track(name="Genie Informatique", code="GI", department_id=dept.id)
        db.session.add(track)
        db.session.commit()
    
    # Ensure academic years exist
    if not AcademicYear.query.filter_by(track_id=track.id).first():
        db.session.add(AcademicYear(name="L1", order=1, track_id=track.id))
        db.session.add(AcademicYear(name="L2", order=2, track_id=track.id))
        db.session.add(AcademicYear(name="L3", order=3, track_id=track.id))
        db.session.commit()
        print("Created academic years")

    # Ensure Track Head User exists
    user = User.query.filter_by(email="demo_head@uir.ac.ma").first()
    if not user:
        user = User(
            email="demo_head@uir.ac.ma",
            first_name="Demo",
            last_name="Head",
            role="teacher",
            is_track_head=True,
            headed_track_id=track.id,
            department_id=dept.id
        )
        user.set_password("password123")
        db.session.add(user)
    else:
        user.is_track_head = True
        user.headed_track_id = track.id
        user.set_password("password123")
    
    db.session.commit()
    print("Demo user ready: demo_head@uir.ac.ma / password123")
