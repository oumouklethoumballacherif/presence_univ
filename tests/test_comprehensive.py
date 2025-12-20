
import unittest
from app import create_app, db
from app.models import User, Department, Track, AcademicYear, Semester, Subject, TeacherSubjectAssignment, Course, Attendance
from app.config import Config
from datetime import datetime

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = True
    SECRET_KEY = 'test-secret-key'

class ComprehensiveTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Define data placeholders
        self.dept = None
        self.track = None
        self.year = None
        self.semester = None
        self.subject = None
        self.teacher = None
        self.student = None

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self, email, password):
        """Helper to login and handle CSRF"""
        response = self.client.get('/login')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.data, 'html.parser')
        token_input = soup.find('input', {'name': 'csrf_token'})
        csrf_token = token_input['value'] if token_input else ''
        
        return self.client.post('/login', data=dict(
            email=email,
            password=password,
            csrf_token=csrf_token
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def get_csrf_token(self, url):
        """Helper to get CSRF token from a specific page"""
        response = self.client.get(url)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.data, 'html.parser')
        token_input = soup.find('input', {'name': 'csrf_token'})
        return token_input['value'] if token_input else ''

    # ================= TESTS =================

    def test_01_admin_setup_structure_and_users(self):
        """Test Admin creating Department, Track, Teacher, Student"""
        # 1. Login Admin
        print("\n[TEST] Admin: Creating Structure and Users")
        admin = User.query.filter_by(email='admin@uir.ac.ma').first() # Created by create_app
        self.login('admin@uir.ac.ma', 'admin123')

        # 2. Create Create Department
        csrf_token = self.get_csrf_token('/admin/departments/create')
        res = self.client.post('/admin/departments/create', data={
            'name': 'Sciences Info',
            'description': 'Dept Informatique',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        self.assertIn(b'Sciences Info', res.data)
        dept = Department.query.filter_by(name='Sciences Info').first()
        self.assertIsNotNone(dept)

        # 3. Create Teacher
        csrf_token = self.get_csrf_token('/admin/teachers/create')
        res = self.client.post('/admin/teachers/create', data={
            'first_name': 'Alan', 'last_name': 'Turing',
            'email': 'alan.turing@uir.ac.ma', 'matricule': 'P001',
            'department_id': dept.id,
            'csrf_token': csrf_token
        }, follow_redirects=True)
        self.assertIn(b'Alan Turing', res.data)
        teacher = User.query.filter_by(email='alan.turing@uir.ac.ma').first()
        
        # Manually set password for teacher (skip email flow in test)
        teacher.set_password('pass123')
        db.session.commit()

        # 4. Create Track
        csrf_token = self.get_csrf_token('/admin/tracks/create')
        res = self.client.post('/admin/tracks/create', data={
            'name': 'Génie Logiciel', 'level': 'm1',
            'department_id': dept.id,
            'csrf_token': csrf_token
        }, follow_redirects=True)
        self.assertIn(b'G\xc3\xa9nie Logiciel', res.data) # Génie Logiciel
        track = Track.query.filter_by(name='Génie Logiciel').first()

        # 5. Create Academic Year & Semester
        csrf_token = self.get_csrf_token(f'/admin/tracks/{track.id}/year/create')
        self.client.post(f'/admin/tracks/{track.id}/year/create', data={
            'name': 'M1 GL', 'order': 1, 'csrf_token': csrf_token
        }, follow_redirects=True)
        year = AcademicYear.query.filter_by(name='M1 GL').first()
        
        csrf_token = self.get_csrf_token(f'/admin/year/{year.id}/semester/create')
        self.client.post(f'/admin/year/{year.id}/semester/create', data={
            'name': 'Semestre 1', 'order': 1, 'csrf_token': csrf_token
        }, follow_redirects=True)
        semester = Semester.query.filter_by(name='Semestre 1').first()

        # 6. Create Student
        csrf_token = self.get_csrf_token('/admin/students/create')
        res = self.client.post('/admin/students/create', data={
            'first_name': 'Grace', 'last_name': 'Hopper',
            'email': 'grace.hopper@uir.ac.ma', 'matricule': 'E001',
            'track_id': track.id, 'academic_year_id': year.id,
            'csrf_token': csrf_token
        }, follow_redirects=True)
        self.assertIn(b'Grace Hopper', res.data)
        student = User.query.filter_by(email='grace.hopper@uir.ac.ma').first()
        # Manually set password
        student.set_password('pass123')
        db.session.commit()

        # 7. Create Subject
        csrf_token = self.get_csrf_token(f'/admin/semester/{semester.id}/subject/create')
        res = self.client.post(f'/admin/semester/{semester.id}/subject/create', data={
            'name': 'Algorithmique', 'code': 'ALG101',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        subject = Subject.query.filter_by(code='ALG101').first()

        # 8. Assign Teacher to Subject
        csrf_token = self.get_csrf_token(f'/admin/subject/{subject.id}/assign')
        res = self.client.post(f'/admin/subject/{subject.id}/assign', data={
            'teacher_id': teacher.id,
            'teaches_cm': 'on', 'teaches_td': 'on',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        self.assertIn(b'Enseignant assign\xc3\xa9', res.data)

        self.logout()
        print("[TEST] Admin Setup Complete")

    def test_02_teacher_workflow(self):
        """Test Teacher creating sessions"""
        # Data Setup (Since tests run independently in this framework usually, we must recreate structure or use setUp)
        # However, making setUp complex slows down. I'll recreate minimal needed here.
        self._setup_data()
        
        print("\n[TEST] Teacher: Creating Session")
        self.login('alan.turing@uir.ac.ma', 'pass123')

        # 1. Create Session for "Algorithmique"
        # URL needs subject_id
        subject = Subject.query.first()
        csrf_token = self.get_csrf_token(f'/teacher/course/create/{subject.id}')
        
        res = self.client.post(f'/teacher/course/create/{subject.id}', data={
            'course_type': 'CM',
            'title': 'Intro to Algo',
            'description': 'Chapter 1',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        self.assertIn(b'S\xc3\xa9ance cr\xc3\xa9\xc3\xa9e', res.data)
        course = Course.query.first()
        self.assertIsNotNone(course)
        self.assertEqual(course.title, 'Intro to Algo')

        self.logout()
        print("[TEST] Teacher Session Created")

    def test_03_student_workflow(self):
        """Test Student flow"""
        self._setup_data()
        
        print("\n[TEST] Student: Dashboard Access")
        self.login('grace.hopper@uir.ac.ma', 'pass123')
        
        res = self.client.get('/student/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Grace Hopper', res.data)
        self.assertIn(b'Algorithmique', res.data) # Should see the subject in stats

        self.logout()


    def _setup_data(self):
        """Helper to set up DB state for tests 2 and 3"""
        # Create Dept
        dept = Department(name='Info')
        db.session.add(dept)
        
        # Create Teacher
        teacher = User(email='alan.turing@uir.ac.ma', first_name='Alan', last_name='Turing', role='teacher', department=dept)
        teacher.set_password('pass123')
        db.session.add(teacher)

        # Create Track & Year
        track = Track(name='GL', level='m1', department=dept)
        db.session.add(track)
        db.session.commit()
        year = AcademicYear(name='M1', order=1, track=track)
        db.session.add(year)
        db.session.commit()
        sem = Semester(name='S1', order=1, academic_year=year)
        db.session.add(sem)
        db.session.commit()

        # Create Student
        student = User(email='grace.hopper@uir.ac.ma', first_name='Grace', last_name='Hopper', role='student', enrolled_tracks=[track], current_year=year)
        student.set_password('pass123')
        db.session.add(student)

        # Create Subject & Assignment
        subject = Subject(name='Algorithmique', code='ALG1', semester=sem)
        db.session.add(subject)
        db.session.commit()

        assign = TeacherSubjectAssignment(teacher=teacher, subject=subject, teaches_cm=True)
        db.session.add(assign)
        db.session.commit()

if __name__ == '__main__':
    unittest.main()
