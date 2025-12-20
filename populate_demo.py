
from app import create_app, db
from app.models import User, Department, Track, AcademicYear, Semester, Subject, TeacherSubjectAssignment, Course, Attendance
from datetime import datetime, timedelta
import random

def create_demo_data():
    app = create_app()
    with app.app_context():
        print("🚀 Starting Demo Data Population...")

        # 1. Departments
        print("- Creating Departments...")
        dept_info = Department(name="Informatique")
        dept_aero = Department(name="Aérospatiale")
        dept_business = Department(name="Business School")
        db.session.add_all([dept_info, dept_aero, dept_business])
        db.session.commit()

        # 2. Tracks (Filières)
        print("- Creating Tracks...")
        # Informatique Tracks
        track_gl = Track(name="Génie Logiciel", level="master", department=dept_info, description="Formation avancée en développement logiciel.")
        track_bd = Track(name="Big Data", level="master", department=dept_info, description="Analytique et gestion de données massives.")
        
        # Aero Tracks
        track_aero_l3 = Track(name="Ingénierie Aérospatiale", level="licence", department=dept_aero)
        
        db.session.add_all([track_gl, track_bd, track_aero_l3])
        db.session.commit()

        # 3. Academic Years & Semesters (Structure)
        print("- Creating Academic Structure...")
        # GL Structure
        year_gl_m1 = AcademicYear(name="M1", order=1, track=track_gl)
        db.session.add(year_gl_m1)
        db.session.commit()
        
        sem_gl_s1 = Semester(name="Semestre 1", order=1, academic_year=year_gl_m1)
        sem_gl_s2 = Semester(name="Semestre 2", order=2, academic_year=year_gl_m1)
        db.session.add_all([sem_gl_s1, sem_gl_s2])
        
        # BD Structure
        year_bd_m1 = AcademicYear(name="M1", order=1, track=track_bd)
        db.session.add(year_bd_m1)
        db.session.commit()
        sem_bd_s1 = Semester(name="Semestre 1", order=1, academic_year=year_bd_m1)
        db.session.add(sem_bd_s1)

        db.session.commit()

        # 4. Teachers
        print("- Creating Teachers...")
        teachers = []
        
        # Info Teachers
        t_alan = User(email="alan.turing@uir.ac.ma", first_name="Alan", last_name="Turing", role="teacher", department=dept_info, matricule="P-INFO-001", is_active=True)
        t_alan.set_password("pass123")
        
        t_ada = User(email="ada.lovelace@uir.ac.ma", first_name="Ada", last_name="Lovelace", role="teacher", department=dept_info, matricule="P-INFO-002", is_active=True)
        t_ada.set_password("pass123")
        
        # Aero Teacher / Track Head
        t_wright = User(email="orville.wright@uir.ac.ma", first_name="Orville", last_name="Wright", role="teacher", department=dept_aero, matricule="P-AERO-001", is_active=True)
        t_wright.set_password("pass123")
        t_wright.is_track_head = True
        t_wright.headed_track_id = track_aero_l3.id # Head of Aero L3
        
        db.session.add_all([t_alan, t_ada, t_wright])
        db.session.commit()

        # 5. Students
        print("- Creating Students...")
        students = []
        names = [
            ("Neo", "Anderson"), ("Trinity", "Moss"), ("Morpheus", "Fish"), ("Agent", "Smith"),
            ("Luke", "Skywalker"), ("Leia", "Organa"), ("Han", "Solo"), ("Darth", "Vader"),
            ("Harry", "Potter"), ("Hermione", "Granger"), ("Ron", "Weasley"), ("Draco", "Malfoy")
        ]
        
        for i, (first, last) in enumerate(names):
            # Assign first 6 to GL, next 4 to BD, last 2 to Aero
            if i < 6:
                track = track_gl
                year = year_gl_m1
            elif i < 10:
                track = track_bd
                year = year_bd_m1
            else:
                track = track_aero_l3
                year = None # No year created for Aero yet for simplicity
                
            s = User(
                email=f"{first.lower()}.{last.lower()}@uir.ac.ma",
                first_name=first,
                last_name=last,
                role="student",
                matricule=f"E2024-{i+1:03d}",
                current_year=year,
                is_active=True
            )
            s.set_password("pass123")
            s.enrolled_tracks.append(track)
            db.session.add(s)
            students.append(s)
            
        db.session.commit()

        # 6. Subjects (Matières)
        print("- Creating Subjects...")
        # GL Subjects
        sub_algo = Subject(name="Algorithmique Avancée", code="INFO-M1-01", description="Complexité et graphes", semester=sem_gl_s1, total_cm=20, total_td=10, total_tp=10)
        sub_web = Subject(name="Dév. Web Fullstack", code="INFO-M1-02", description="React & Flask", semester=sem_gl_s1, total_cm=16, total_td=0, total_tp=24)
        sub_bdd = Subject(name="Bases de Données (SQL)", code="INFO-M1-03", description="Modélisation et requêtes", semester=sem_gl_s2, total_cm=18, total_td=18, total_tp=0)
        
        # BD Subjects
        sub_mining = Subject(name="Data Mining", code="DATA-M1-01", description="Extraction de connaissances", semester=sem_bd_s1, total_cm=20, total_td=10, total_tp=0)
        
        db.session.add_all([sub_algo, sub_web, sub_bdd, sub_mining])
        db.session.commit()

        # 7. Assignments (Assign Teachers to Subjects)
        print("- Assigning Teachers...")
        # Alan teaches Algo (CM+TD) and Data Mining
        a1 = TeacherSubjectAssignment(teacher=t_alan, subject=sub_algo, teaches_cm=True, teaches_td=True)
        a2 = TeacherSubjectAssignment(teacher=t_alan, subject=sub_mining, teaches_cm=True)
        
        # Ada teaches Web (CM+TP) and Algo (TP)
        a3 = TeacherSubjectAssignment(teacher=t_ada, subject=sub_web, teaches_cm=True, teaches_tp=True)
        a4 = TeacherSubjectAssignment(teacher=t_ada, subject=sub_algo, teaches_tp=True)
        
        db.session.add_all([a1, a2, a3, a4])
        db.session.commit()

        # 8. Create some Past Sessions (Courses) for History
        print("- Creating Past Sessions...")
        # 1 week ago - Algo CM
        c_algo_past = Course(
            subject=sub_algo, teacher=t_alan, course_type='CM', 
            title="Introduction aux Graphes", 
            status='completed',
            started_at=datetime.utcnow() - timedelta(days=7, hours=2),
            ended_at=datetime.utcnow() - timedelta(days=7),
            scheduled_date=(datetime.utcnow() - timedelta(days=7)).date()
        )
        
        # Yesterday - Web TP
        c_web_past = Course(
            subject=sub_web, teacher=t_ada, course_type='TP', 
            title="TP1: Setup React", 
            status='completed',
            started_at=datetime.utcnow() - timedelta(days=1, hours=2),
            ended_at=datetime.utcnow() - timedelta(days=1),
            scheduled_date=(datetime.utcnow() - timedelta(days=1)).date()
        )
        
        db.session.add_all([c_algo_past, c_web_past])
        db.session.commit()
        
        # 9. Attendance Records
        print("- Marking Attendance...")
        # Only for GL students (first 6)
        gl_students = students[:6]
        
        # Algo Past Session: All present except one absent, one late
        for idx, student in enumerate(gl_students):
            status = 'present'
            if idx == 3: status = 'absent'
            if idx == 4: status = 'late'
            
            att = Attendance(course=c_algo_past, student=student, status=status, scanned_at=c_algo_past.started_at)
            db.session.add(att)
            
        db.session.commit()

        print("\n✅ DEMO DATA POPULATED SUCCESSFULLY!")
        print("You can login with:")
        print("  Admin:   admin@uir.ac.ma / admin123")
        print("  Teacher: alan.turing@uir.ac.ma / pass123")
        print("  Student: neo.anderson@uir.ac.ma / pass123")

if __name__ == '__main__':
    create_demo_data()
