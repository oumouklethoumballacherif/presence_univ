from app import create_app, db
from app.models import User, TeacherSubjectAssignment, Subject, Semester, AcademicYear, Track

app = create_app()

with app.app_context():
    # Get the logged in teacher (assuming it's the first one or a specific email if known, but I'll list all teachers with assignments)
    teachers = User.query.filter_by(role='teacher').all()
    print(f"Found {len(teachers)} teachers.")

    for teacher in teachers:
        print(f"\nChecking assignments for: {teacher.full_name} ({teacher.email})")
        assignments = TeacherSubjectAssignment.query.filter_by(teacher_id=teacher.id).all()
        print(f"  Assignments found: {len(assignments)}")
        
        for assignment in assignments:
            subject = assignment.subject
            print(f"    - Subject: {subject.name} (ID: {subject.id})")
            if subject.semester:
                sem = subject.semester
                print(f"      - Semester: {sem.name} (ID: {sem.id})")
                if sem.academic_year:
                    year = sem.academic_year
                    print(f"        - Year: {year.name} (ID: {year.id})")
                    if year.track:
                        track = year.track
                        print(f"          - Track: {track.name} (ID: {track.id})")
                    else:
                        print("          - Track: None (Broken Link!)")
                else:
                    print("        - Year: None (Broken Link!)")
            else:
                print("      - Semester: None (Broken Link!)")
