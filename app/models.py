from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

db = SQLAlchemy()

# Association tables
teacher_tracks = db.Table('teacher_tracks',
    db.Column('teacher_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('track_id', db.Integer, db.ForeignKey('tracks.id'), primary_key=True)
)

student_tracks = db.Table('student_tracks',
    db.Column('student_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('track_id', db.Integer, db.ForeignKey('tracks.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    matricule = db.Column(db.String(50), unique=True)  # Student/Teacher ID
    
    # Role: admin, teacher, student
    role = db.Column(db.String(20), nullable=False, default='teacher')
    
    # Extension roles (for teachers)
    is_dept_head = db.Column(db.Boolean, default=False)
    is_track_head = db.Column(db.Boolean, default=False)
    
    # Relationships
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    department = db.relationship('Department', back_populates='teachers', foreign_keys=[department_id])
    
    # Department headed (if dept head)
    headed_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    headed_department = db.relationship('Department', back_populates='head', foreign_keys=[headed_department_id])
    
    # Track headed (if track head)
    headed_track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'))
    headed_track = db.relationship('Track', back_populates='head', foreign_keys=[headed_track_id])
    
    # Tracks assigned to (for teachers)
    assigned_tracks = db.relationship('Track', secondary=teacher_tracks, back_populates='assigned_teachers')
    
    # Track enrolled in (for students)
    enrolled_tracks = db.relationship('Track', secondary=student_tracks, back_populates='students')
    
    # Token for password creation/reset
    token = db.Column(db.String(100), unique=True)
    token_expiry = db.Column(db.DateTime)
    
    # Current Academic Year (L1, L2, M1, etc.)
    current_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'))
    current_year = db.relationship('AcademicYear', foreign_keys=[current_year_id])
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Subject assignments
    subject_assignments = db.relationship('TeacherSubjectAssignment', back_populates='teacher', cascade='all, delete-orphan')
    
    # Attendances (for students)
    attendances = db.relationship('Attendance', back_populates='student')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_token(self, expiry_hours=24):
        self.token = secrets.token_urlsafe(32)
        self.token_expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
        return self.token
    
    def verify_token(self):
        if self.token and self.token_expiry:
            return datetime.utcnow() < self.token_expiry
        return False
    
    def clear_token(self):
        self.token = None
        self.token_expiry = None
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def dashboard_tabs(self):
        """Return list of dashboard tabs based on roles."""
        tabs = ['mes_cours']
        if self.is_dept_head and self.headed_department:
            tabs.append('gestion_departement')
        if self.is_track_head and self.headed_track:
            tabs.append('gestion_filiere')
        return tabs
    
    def __repr__(self):
        return f'<User {self.email}>'


class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Teachers in this department
    teachers = db.relationship('User', back_populates='department', foreign_keys='User.department_id')
    
    # Department head
    head = db.relationship('User', back_populates='headed_department', foreign_keys='User.headed_department_id', uselist=False)
    
    # Tracks in this department
    tracks = db.relationship('Track', back_populates='department', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Department {self.name}>'


class Track(db.Model):
    """Filière"""
    __tablename__ = 'tracks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(20), nullable=False, default='licence')  # licence, master, doctorat
    description = db.Column(db.Text)
    
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    department = db.relationship('Department', back_populates='tracks')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Track head
    head = db.relationship('User', back_populates='headed_track', foreign_keys='User.headed_track_id', uselist=False)
    
    # Teachers assigned to this track
    assigned_teachers = db.relationship('User', secondary=teacher_tracks, back_populates='assigned_tracks')
    
    # Students enrolled in this track
    students = db.relationship('User', secondary=student_tracks, back_populates='enrolled_tracks')
    
    # Academic years
    academic_years = db.relationship('AcademicYear', back_populates='track', cascade='all, delete-orphan')
    
    @property
    def level_display(self):
        """Display name for level"""
        levels = {'licence': 'Licence', 'master': 'Master', 'doctorat': 'Doctorat'}
        return levels.get(self.level, self.level)
    
    @staticmethod
    def get_academic_structure(level):
        """Get years and semesters structure for a given level"""
        structures = {
            'licence': {
                'years': [('L1', '1ère année Licence'), ('L2', '2ème année Licence'), ('L3', '3ème année Licence')],
                'semesters_per_year': 2
            },
            'master': {
                'years': [('M1', '1ère année Master'), ('M2', '2ème année Master')],
                'semesters_per_year': 2
            },
            'doctorat': {
                'years': [('D1', '1ère année Doctorat'), ('D2', '2ème année Doctorat'), ('D3', '3ème année Doctorat')],
                'semesters_per_year': 2
            }
        }
        return structures.get(level, structures['licence'])
    
    def __repr__(self):
        return f'<Track {self.name}>'


class AcademicYear(db.Model):
    """Année académique"""
    __tablename__ = 'academic_years'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., "1ère année", "2ème année"
    order = db.Column(db.Integer, default=1)  # For sorting
    
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'), nullable=False)
    track = db.relationship('Track', back_populates='academic_years')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Semesters
    semesters = db.relationship('Semester', back_populates='academic_year', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AcademicYear {self.name}>'


class Semester(db.Model):
    __tablename__ = 'semesters'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., "Semestre 1", "Semestre 2"
    order = db.Column(db.Integer, default=1)
    
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False)
    academic_year = db.relationship('AcademicYear', back_populates='semesters')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Subjects
    subjects = db.relationship('Subject', back_populates='semester', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Semester {self.name}>'


class Subject(db.Model):
    """Matière"""
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)
    semester = db.relationship('Semester', back_populates='subjects')
    
    # Session counts
    total_cm = db.Column(db.Integer, default=0)  # Cours Magistraux
    total_td = db.Column(db.Integer, default=0)  # Travaux Dirigés
    total_tp = db.Column(db.Integer, default=0)  # Travaux Pratiques
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Teacher assignments
    teacher_assignments = db.relationship('TeacherSubjectAssignment', back_populates='subject', cascade='all, delete-orphan')
    
    # Courses (sessions)
    courses = db.relationship('Course', back_populates='subject', cascade='all, delete-orphan')
    
    @property
    def total_sessions(self):
        return self.total_cm + self.total_td + self.total_tp
    
    def __repr__(self):
        return f'<Subject {self.name}>'


class TeacherSubjectAssignment(db.Model):
    """Links teachers to subjects they teach"""
    __tablename__ = 'teacher_subject_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    
    # What types the teacher handles for this subject
    teaches_cm = db.Column(db.Boolean, default=False)
    teaches_td = db.Column(db.Boolean, default=False)
    teaches_tp = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    teacher = db.relationship('User', back_populates='subject_assignments')
    subject = db.relationship('Subject', back_populates='teacher_assignments')
    
    __table_args__ = (db.UniqueConstraint('teacher_id', 'subject_id'),)


class Course(db.Model):
    """Session de cours"""
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Type: CM, TD, TP
    course_type = db.Column(db.String(10), nullable=False)
    
    # Status: pending, active, completed
    status = db.Column(db.String(20), default='pending')
    
    # Session info
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    scheduled_date = db.Column(db.DateTime)
    
    # QR code token (regenerated every 15s when active)
    qr_token = db.Column(db.String(100))
    qr_generated_at = db.Column(db.DateTime)
    
    # Timestamps
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    subject = db.relationship('Subject', back_populates='courses')
    teacher = db.relationship('User')
    attendances = db.relationship('Attendance', back_populates='course', cascade='all, delete-orphan')
    
    def generate_qr_token(self):
        """Generate new QR token"""
        self.qr_token = secrets.token_urlsafe(16)
        self.qr_generated_at = datetime.utcnow()
        return self.qr_token
    
    def is_qr_valid(self, token):
        """Check if QR token is valid (within 15s window)"""
        if not self.qr_token or not self.qr_generated_at:
            return False
        if token != self.qr_token:
            return False
        # Token is valid for 20 seconds (15s + 5s grace period)
        return (datetime.utcnow() - self.qr_generated_at).total_seconds() <= 20
    
    def __repr__(self):
        return f'<Course {self.subject.name} - {self.course_type}>'


class Attendance(db.Model):
    __tablename__ = 'attendances'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Status: present, absent
    status = db.Column(db.String(20), default='absent')
    
    # When the student scanned
    scanned_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    course = db.relationship('Course', back_populates='attendances')
    student = db.relationship('User', back_populates='attendances')
    
    __table_args__ = (db.UniqueConstraint('course_id', 'student_id'),)
    
    def __repr__(self):
        return f'<Attendance {self.student.email} - {self.status}>'


class AttendanceToken(db.Model):
    """Temporary token for dynamic QR code attendance"""
    __tablename__ = 'attendance_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False)  # UUID
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    course = db.relationship('Course', backref=db.backref('qr_tokens', cascade='all, delete-orphan'))
    
    def is_valid(self):
        return datetime.utcnow() < self.expires_at


def calculate_rattrapage_status(student_id, subject_id):
    """
    Calculate if a student is in rattrapage for a subject.
    Rules:
    - >25% absences in CM+TD -> Rattrapage
    - >=2 absences in TP -> Rattrapage
    """
    subject = Subject.query.get(subject_id)
    if not subject:
        return False, {}
    
    # Get completed courses for this subject
    completed_courses = Course.query.filter_by(
        subject_id=subject_id,
        status='completed'
    ).all()
    
    cm_td_total = 0
    cm_td_absent = 0
    tp_absent = 0
    
    for course in completed_courses:
        attendance = Attendance.query.filter_by(
            course_id=course.id,
            student_id=student_id
        ).first()
        
        if course.course_type in ['CM', 'TD']:
            cm_td_total += 1
            if attendance:
                if attendance.status == 'absent':
                    cm_td_absent += 1
                elif attendance.status == 'late':
                    cm_td_absent += 0.5
        elif course.course_type == 'TP':
            if attendance:
                if attendance.status == 'absent':
                    tp_absent += 1
                elif attendance.status == 'late':
                    tp_absent += 0.5
    
    # Check rattrapage conditions
    # Logic Update: User wants Rattrapage if Presence Rate < 25% (CM/TD)
    # OR if TP absences >= 2
    
    # Calculate Presence Rate (considering Late as 0.5 presence)
    # cm_td_absent now includes 0.5 for lates, so:
    cm_td_presence_count = cm_td_total - cm_td_absent
    cm_td_rate = cm_td_presence_count / cm_td_total if cm_td_total > 0 else 1.0
    
    is_rattrapage = cm_td_rate < 0.25 or tp_absent >= 2
    
    stats = {
        'cm_td_total': cm_td_total,
        'cm_td_absent': cm_td_absent,
        'cm_td_rate': cm_td_rate,
        'tp_absent': tp_absent,
        'is_rattrapage': is_rattrapage
    }
    
    return is_rattrapage, stats


def calculate_attendance_grade(student_id, subject_id):
    """
    Calculate attendance grade out of 20 for a subject.
    Based on presence rate.
    """
    subject = Subject.query.get(subject_id)
    if not subject:
        return 0
    
    completed_courses = Course.query.filter_by(
        subject_id=subject_id,
        status='completed'
    ).all()
    
    cm_td_total = 0
    cm_td_points = 0
    
    for course in completed_courses:
        if course.course_type in ['CM', 'TD']:
            cm_td_total += 1
            attendance = Attendance.query.filter_by(
                course_id=course.id,
                student_id=student_id
            ).first()
            
            if attendance:
                if attendance.status == 'present':
                    cm_td_points += 1
                elif attendance.status == 'late':
                    cm_td_points += 0.5
    
    if cm_td_total == 0:
        return 20.0
        
    rate = cm_td_points / cm_td_total
    return round(rate * 20, 2)
