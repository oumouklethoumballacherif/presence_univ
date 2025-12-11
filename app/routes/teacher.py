from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import (db, User, Department, Track, AcademicYear, Semester, 
                        Subject, TeacherSubjectAssignment, Course, Attendance, AttendanceToken,
                        calculate_rattrapage_status, calculate_attendance_grade)
from app.utils.decorators import teacher_required, dept_head_required, track_head_required
from app.utils.email import send_password_creation_email
from app.utils.qr_generator import generate_attendance_qr
from datetime import datetime, timedelta
import uuid
import openpyxl
from io import BytesIO

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')


# ==================== DASHBOARD ====================

@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    """Teacher dashboard with courses and dynamic tabs"""
    # Get filter parameters
    track_id = request.args.get('track_id', type=int)
    year_id = request.args.get('academic_year_id', type=int)
    semester_id = request.args.get('semester_id', type=int)
    
    # Get subjects assigned to this teacher
    assignments = TeacherSubjectAssignment.query.filter_by(teacher_id=current_user.id).all()
    
    subjects = []
    # Collect available filter options
    available_tracks = set()
    available_years = set()
    available_semesters = set()

    for assignment in assignments:
        subject = assignment.subject
        track = subject.semester.academic_year.track
        year = subject.semester.academic_year
        semester = subject.semester
        
        # Add to available options sets
        available_tracks.add(track)
        
        # Filter Logic
        if track_id and track.id != track_id:
            continue
            
        # If track matches (or no track selected), add relevant years
        available_years.add(year)

        if year_id and year.id != year_id:
            continue
            
        # If year matches (or no year selected), add relevant semesters
        available_semesters.add(semester)

        if semester_id and semester.id != semester_id:
            continue
            
        subjects.append({
            'subject': subject,
            'assignment': assignment,
            'track': track,
            'academic_year': year,
            'semester': semester
        })
    
    # Dynamic tabs
    tabs = current_user.dashboard_tabs
    
    return render_template('teacher/dashboard.html',
                          subjects=subjects,
                          tracks=list(available_tracks),
                          years=list(available_years) if track_id else [],
                          semesters=list(available_semesters) if year_id else [],
                          tabs=tabs,
                          selected_track=track_id,
                          selected_year=year_id,
                          selected_semester=semester_id)


@teacher_bp.route('/api/filter-options')
@login_required
@teacher_required
def get_filter_options():
    """API to get filter options based on selection"""
    track_id = request.args.get('track_id', type=int)
    year_id = request.args.get('year_id', type=int)
    semester_id = request.args.get('semester_id', type=int)
    
    # Get all assignments for security check
    assignments = TeacherSubjectAssignment.query.filter_by(teacher_id=current_user.id).all()
    
    years_data = set()
    semesters_data = set()
    subjects_data = set()
    
    for assignment in assignments:
        subject = assignment.subject
        track = subject.semester.academic_year.track
        year = subject.semester.academic_year
        semester = subject.semester
        
        # Filter by track if provided
        if track_id and track.id != track_id:
            continue
            
        years_data.add(year)
        
        # Filter by year if provided
        if year_id and year.id != year_id:
            continue
            
        semesters_data.add(semester)

        # Filter by semester if provided
        if semester_id and semester.id != semester_id:
            continue
            
        subjects_data.add(subject)
        
    return jsonify({
        'years': [{'id': y.id, 'name': f"{y.name} - {y.track.name}"} for y in sorted(list(years_data), key=lambda x: (x.track.name, x.order))],
        'semesters': [{'id': s.id, 'name': f"{s.name} - {s.academic_year.name}"} for s in sorted(list(semesters_data), key=lambda x: (x.academic_year.name, x.order))],
        'subjects': [{'id': s.id, 'name': s.name} for s in sorted(list(subjects_data), key=lambda x: x.name)]
    })


# ==================== COURSE MANAGEMENT ====================

@teacher_bp.route('/courses')
@login_required
@teacher_required
def courses():
    """List all courses for this teacher with filtering"""
    # Get filter parameters
    track_id = request.args.get('track_id', type=int)
    year_id = request.args.get('academic_year_id', type=int)
    semester_id = request.args.get('semester_id', type=int)
    subject_id = request.args.get('subject_id', type=int)
    status = request.args.get('status')
    
    # Debugging logs
    print(f"DEBUG FILTERS: Track={track_id}, Year={year_id}, Semester={semester_id}, Subject={subject_id}, Status={status}")

    # Base query
    query = Course.query.filter_by(teacher_id=current_user.id)

    # Apply filters
    if track_id or year_id or semester_id or subject_id:
        query = query.join(Subject).join(Semester).join(AcademicYear).join(Track)
        
        if track_id:
            query = query.filter(Track.id == track_id)
        if year_id:
            query = query.filter(AcademicYear.id == year_id)
        if semester_id:
            query = query.filter(Semester.id == semester_id)
        if subject_id:
            query = query.filter(Subject.id == subject_id)
            
    if status and status.strip():
        query = query.filter(Course.status == status)

    courses = query.order_by(Course.created_at.desc()).all()
    print(f"DEBUG: Found {len(courses)} courses")

    # Get available filter options (reuse logic for consistency)
    assignments = TeacherSubjectAssignment.query.filter_by(teacher_id=current_user.id).all()
    available_tracks = set()
    available_years = set()
    available_semesters = set()
    available_subjects = set()

    for assignment in assignments:
        subject = assignment.subject
        track = subject.semester.academic_year.track
        year = subject.semester.academic_year
        semester = subject.semester
        
        available_tracks.add(track)
        
        if track_id and track.id != track_id:
            continue
        available_years.add(year)

        if year_id and year.id != year_id:
            continue
        available_semesters.add(semester)

        if semester_id and semester.id != semester_id:
            continue
        available_subjects.add(subject)

    return render_template('teacher/courses.html', 
                          courses=courses,
                          tracks=list(available_tracks),
                          years=list(available_years),
                          semesters=list(available_semesters),
                          subjects=list(available_subjects),
                          selected_track=track_id,
                          selected_year=year_id,
                          selected_semester=semester_id,
                          selected_subject=subject_id,
                          selected_status=status)


@teacher_bp.route('/course/create/<int:subject_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_course(subject_id):
    """Create a new course session"""
    subject = Subject.query.get_or_404(subject_id)
    
    # Verify teacher is assigned
    assignment = TeacherSubjectAssignment.query.filter_by(
        teacher_id=current_user.id,
        subject_id=subject_id
    ).first()
    
    if not assignment:
        flash('Vous n\'êtes pas assigné à cette matière.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    if request.method == 'POST':
        course_type = request.form.get('course_type')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        
        if course_type not in ['CM', 'TD', 'TP']:
            flash('Type de cours invalide.', 'danger')
            return render_template('teacher/course_form.html', subject=subject, assignment=assignment)
        
        # Check if teacher can teach this type
        can_teach = (
            (course_type == 'CM' and assignment.teaches_cm) or
            (course_type == 'TD' and assignment.teaches_td) or
            (course_type == 'TP' and assignment.teaches_tp)
        )
        
        if not can_teach:
            flash(f'Vous n\'êtes pas autorisé à enseigner les {course_type}.', 'danger')
            return render_template('teacher/course_form.html', subject=subject, assignment=assignment)
        
        course = Course(
            subject_id=subject_id,
            teacher_id=current_user.id,
            course_type=course_type,
            title=title or f"{subject.name} - {course_type}",
            description=description,
            status='pending'
        )
        
        db.session.add(course)
        db.session.commit()
        
        flash('Séance créée avec succès!', 'success')
        return redirect(url_for('teacher.course_detail', id=course.id))
    
    return render_template('teacher/course_form.html', subject=subject, assignment=assignment)


@teacher_bp.route('/course/<int:id>')
@login_required
@teacher_required
def course_detail(id):
    """View course details"""
    course = Course.query.get_or_404(id)
    
    if course.teacher_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    # Get track students
    track = course.subject.semester.academic_year.track
    students = track.students
    
    # Get attendance data
    attendance_data = []
    for student in students:
        attendance = Attendance.query.filter_by(
            course_id=course.id,
            student_id=student.id
        ).first()
        attendance_data.append({
            'student': student,
            'attendance': attendance
        })
    
    return render_template('teacher/course_detail.html', 
                          course=course,
                          attendance_data=attendance_data)


@teacher_bp.route('/course/<int:id>/start', methods=['POST'])
@login_required
@teacher_required
def start_course(id):
    """Start a course session and generate QR code"""
    course = Course.query.get_or_404(id)
    
    if course.teacher_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    if course.status != 'pending':
        flash('Cette séance a déjà été démarrée ou terminée.', 'warning')
        return redirect(url_for('teacher.course_detail', id=id))
    
    # Create attendance records for all students
    track = course.subject.semester.academic_year.track
    for student in track.students:
        attendance = Attendance(
            course_id=course.id,
            student_id=student.id,
            status='absent'
        )
        db.session.add(attendance)
    
    course.status = 'active'
    course.started_at = datetime.utcnow()
    
    # Generate initial token using AttendanceToken
    token_str = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(seconds=15)
    
    new_token = AttendanceToken(
        token=token_str,
        course_id=course.id,
        expires_at=expires_at
    )
    db.session.add(new_token)
    db.session.commit()
    
    return redirect(url_for('teacher.qr_display', id=id))


@teacher_bp.route('/course/<int:id>/qr')
@login_required
@teacher_required
def qr_display(id):
    """Display QR code for active course"""
    course = Course.query.get_or_404(id)
    
    if course.teacher_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    if course.status != 'active':
        flash('La séance n\'est pas active.', 'warning')
        return redirect(url_for('teacher.course_detail', id=id))
    
    # Get the latest valid token or generate a new one
    latest_token = AttendanceToken.query.filter_by(course_id=id).order_by(AttendanceToken.created_at.desc()).first()
    
    if not latest_token or not latest_token.is_valid():
        token_str = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=15)
        latest_token = AttendanceToken(
            token=token_str,
            course_id=id,
            expires_at=expires_at
        )
        db.session.add(latest_token)
        db.session.commit()
    
    qr_image = generate_attendance_qr(course.id, latest_token.token)
    
    return render_template('teacher/qr_display.html', course=course, qr_image=qr_image)


@teacher_bp.route('/course/<int:id>/refresh-qr', methods=['POST'])
@login_required
@teacher_required
def refresh_qr(id):
    """Refresh QR code token (called every 15 seconds)"""
    course = Course.query.get_or_404(id)
    
    if course.teacher_id != current_user.id or course.status != 'active':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Generate new token
    token_str = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(seconds=15)
    
    new_token = AttendanceToken(
        token=token_str,
        course_id=course.id,
        expires_at=expires_at
    )
    db.session.add(new_token)
    
    # Clean up old tokens (optional, keeping last 5 mins for safety)
    # db.session.query(AttendanceToken).filter(AttendanceToken.expires_at < datetime.utcnow() - timedelta(minutes=5)).delete()
    
    db.session.commit()
    
    qr_image = generate_attendance_qr(course.id, new_token.token)
    
    return jsonify({
        'qr_image': qr_image,
        'token': new_token.token,
        'expires_at': new_token.expires_at.isoformat()
    })


@teacher_bp.route('/course/<int:id>/end', methods=['POST'])
@login_required
@teacher_required
def end_course(id):
    """End a course session"""
    course = Course.query.get_or_404(id)
    
    if course.teacher_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    if course.status != 'active':
        flash('Cette séance n\'est pas active.', 'warning')
        return redirect(url_for('teacher.course_detail', id=id))
    
    course.status = 'completed'
    course.ended_at = datetime.utcnow()
    course.qr_token = None
    db.session.commit()
    
    flash('Séance terminée avec succès!', 'success')
    return redirect(url_for('teacher.course_detail', id=id))


# ==================== ATTENDANCE CONSULTATION ====================

@teacher_bp.route('/subject/<int:id>/attendance')
@login_required
@teacher_required
def subject_attendance(id):
    """View attendance for a subject"""
    subject = Subject.query.get_or_404(id)
    
    # Verify teacher is assigned
    assignment = TeacherSubjectAssignment.query.filter_by(
        teacher_id=current_user.id,
        subject_id=id
    ).first()
    
    if not assignment:
        flash('Vous n\'êtes pas assigné à cette matière.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    # Get completed courses
    courses = Course.query.filter_by(
        subject_id=id,
        status='completed'
    ).order_by(Course.started_at.desc()).all()
    
    # Get students and their attendance
    track = subject.semester.academic_year.track
    students_data = []
    
    for student in track.students:
        student_attendance = {
            'student': student,
            'courses': []
        }
        
        total = 0
        present = 0
        
        for course in courses:
            attendance = Attendance.query.filter_by(
                course_id=course.id,
                student_id=student.id
            ).first()
            
            if attendance:
                total += 1
                if attendance.status == 'present':
                    present += 1
            
            student_attendance['courses'].append({
                'course': course,
                'attendance': attendance
            })
        
        is_rattrapage, stats = calculate_rattrapage_status(student.id, id)
        grade = calculate_attendance_grade(student.id, id)
        
        student_attendance['total'] = total
        student_attendance['present'] = present
        student_attendance['rate'] = (present / total * 100) if total > 0 else 100
        student_attendance['is_rattrapage'] = is_rattrapage
        student_attendance['grade'] = grade
        
        students_data.append(student_attendance)
    
    return render_template('teacher/subject_attendance.html',
                          subject=subject,
                          courses=courses,
                          students_data=students_data)


# ==================== DEPARTMENT HEAD ROUTES ====================

@teacher_bp.route('/department')
@login_required
@dept_head_required
def department_management():
    """Department head management page"""
    dept = current_user.headed_department
    tracks = Track.query.filter_by(department_id=dept.id).order_by(Track.name).all()
    teachers = User.query.filter_by(role='teacher', department_id=dept.id).order_by(User.last_name).all()
    
    return render_template('teacher/department_management.html',
                          department=dept,
                          tracks=tracks,
                          teachers=teachers)


@teacher_bp.route('/department/track/create', methods=['GET', 'POST'])
@login_required
@dept_head_required
def create_track():
    """Create a new track (filière)"""
    dept = current_user.headed_department
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '').strip()
        
        if not name or not code:
            flash('Le nom et le code sont obligatoires.', 'danger')
            return render_template('teacher/track_form.html', department=dept)
        
        if Track.query.filter_by(code=code, department_id=dept.id).first():
            flash('Une filière avec ce code existe déjà dans ce département.', 'danger')
            return render_template('teacher/track_form.html', department=dept)
        
        track = Track(
            name=name,
            code=code,
            description=description,
            department_id=dept.id
        )
        db.session.add(track)
        db.session.commit()
        
        flash(f'Filière "{name}" créée avec succès!', 'success')
        return redirect(url_for('teacher.department_management'))
    
    return render_template('teacher/track_form.html', department=dept)


@teacher_bp.route('/department/track/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@dept_head_required
def edit_track(id):
    """Edit a track"""
    track = Track.query.get_or_404(id)
    dept = current_user.headed_department
    
    if track.department_id != dept.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.department_management'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '').strip()
        
        if not name or not code:
            flash('Le nom et le code sont obligatoires.', 'danger')
            return render_template('teacher/track_form.html', track=track, department=dept)
        
        existing = Track.query.filter_by(code=code, department_id=dept.id).first()
        if existing and existing.id != track.id:
            flash('Une filière avec ce code existe déjà.', 'danger')
            return render_template('teacher/track_form.html', track=track, department=dept)
        
        track.name = name
        track.code = code
        track.description = description
        db.session.commit()
        
        flash(f'Filière modifiée avec succès!', 'success')
        return redirect(url_for('teacher.department_management'))
    
    return render_template('teacher/track_form.html', track=track, department=dept)


@teacher_bp.route('/department/track/<int:id>/delete', methods=['POST'])
@login_required
@dept_head_required
def delete_track(id):
    """Delete a track"""
    track = Track.query.get_or_404(id)
    dept = current_user.headed_department
    
    if track.department_id != dept.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.department_management'))
    
    name = track.name
    db.session.delete(track)
    db.session.commit()
    
    flash(f'Filière "{name}" supprimée avec succès!', 'success')
    return redirect(url_for('teacher.department_management'))


@teacher_bp.route('/department/track/<int:id>/head', methods=['GET', 'POST'])
@login_required
@dept_head_required
def assign_track_head(id):
    """Assign track head"""
    track = Track.query.get_or_404(id)
    dept = current_user.headed_department
    
    if track.department_id != dept.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.department_management'))
    
    teachers = User.query.filter_by(role='teacher', department_id=dept.id).order_by(User.last_name).all()
    
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id', type=int)
        
        if teacher_id:
            new_head = User.query.get(teacher_id)
            if not new_head or new_head.department_id != dept.id:
                flash('Enseignant invalide.', 'danger')
                return redirect(url_for('teacher.assign_track_head', id=id))
            
            # Remove old head
            old_head = track.head
            if old_head:
                old_head.is_track_head = False
                old_head.headed_track_id = None
            
            # Assign new head
            new_head.is_track_head = True
            new_head.headed_track_id = track.id
            
            db.session.commit()
            flash(f'{new_head.full_name} est maintenant chef de la filière "{track.name}".', 'success')
        else:
            if track.head:
                track.head.is_track_head = False
                track.head.headed_track_id = None
                db.session.commit()
                flash('Chef de filière retiré.', 'info')
        
        return redirect(url_for('teacher.department_management'))
    
    return render_template('teacher/assign_head.html', track=track, teachers=teachers, type='track')


@teacher_bp.route('/department/track/<int:id>/teachers', methods=['GET', 'POST'])
@login_required
@dept_head_required
def assign_track_teachers(id):
    """Assign teachers to a track"""
    track = Track.query.get_or_404(id)
    dept = current_user.headed_department
    
    if track.department_id != dept.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.department_management'))
    
    teachers = User.query.filter_by(role='teacher', department_id=dept.id).order_by(User.last_name).all()
    
    if request.method == 'POST':
        selected_ids = request.form.getlist('teacher_ids', type=int)
        
        # Clear current assignments
        track.assigned_teachers = []
        
        # Add selected teachers
        for tid in selected_ids:
            teacher = User.query.get(tid)
            if teacher and teacher.department_id == dept.id:
                track.assigned_teachers.append(teacher)
        
        db.session.commit()
        flash('Enseignants assignés avec succès!', 'success')
        return redirect(url_for('teacher.department_management'))
    
    return render_template('teacher/assign_teachers.html', track=track, teachers=teachers)


# ==================== TRACK HEAD ROUTES ====================

@teacher_bp.route('/track')
@login_required
@track_head_required
def track_management():
    """Track head management page"""
    track = current_user.headed_track
    academic_years = AcademicYear.query.filter_by(track_id=track.id).order_by(AcademicYear.order).all()
    
    return render_template('teacher/track_management.html',
                          track=track,
                          academic_years=academic_years)


@teacher_bp.route('/track/year/create', methods=['GET', 'POST'])
@login_required
@track_head_required
def create_academic_year():
    """Create academic year"""
    track = current_user.headed_track
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        order = request.form.get('order', type=int, default=1)
        
        if not name:
            flash('Le nom est obligatoire.', 'danger')
            return render_template('teacher/academic_year_form.html', track=track)
        
        year = AcademicYear(
            name=name,
            order=order,
            track_id=track.id
        )
        db.session.add(year)
        db.session.commit()
        
        flash(f'Année "{name}" créée avec succès!', 'success')
        return redirect(url_for('teacher.track_management'))
    
    return render_template('teacher/academic_year_form.html', track=track)


@teacher_bp.route('/track/year/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@track_head_required
def edit_academic_year(id):
    """Edit academic year"""
    year = AcademicYear.query.get_or_404(id)
    track = current_user.headed_track
    
    if year.track_id != track.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.track_management'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        order = request.form.get('order', type=int, default=1)
        
        if not name:
            flash('Le nom est obligatoire.', 'danger')
            return render_template('teacher/academic_year_form.html', year=year, track=track)
        
        year.name = name
        year.order = order
        db.session.commit()
        
        flash('Année modifiée avec succès!', 'success')
        return redirect(url_for('teacher.track_management'))
    
    return render_template('teacher/academic_year_form.html', year=year, track=track)


@teacher_bp.route('/track/year/<int:id>/delete', methods=['POST'])
@login_required
@track_head_required
def delete_academic_year(id):
    """Delete academic year"""
    year = AcademicYear.query.get_or_404(id)
    track = current_user.headed_track
    
    if year.track_id != track.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.track_management'))
    
    name = year.name
    db.session.delete(year)
    db.session.commit()
    
    flash(f'Année "{name}" supprimée avec succès!', 'success')
    return redirect(url_for('teacher.track_management'))


@teacher_bp.route('/track/semester/create/<int:year_id>', methods=['GET', 'POST'])
@login_required
@track_head_required
def create_semester(year_id):
    """Create semester"""
    year = AcademicYear.query.get_or_404(year_id)
    track = current_user.headed_track
    
    if year.track_id != track.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.track_management'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        order = request.form.get('order', type=int, default=1)
        
        if not name:
            flash('Le nom est obligatoire.', 'danger')
            return render_template('teacher/semester_form.html', year=year, track=track)
        
        semester = Semester(
            name=name,
            order=order,
            academic_year_id=year_id
        )
        db.session.add(semester)
        db.session.commit()
        
        flash(f'Semestre "{name}" créé avec succès!', 'success')
        return redirect(url_for('teacher.track_management'))
    
    return render_template('teacher/semester_form.html', year=year, track=track)


@teacher_bp.route('/track/subject/create/<int:semester_id>', methods=['GET', 'POST'])
@login_required
@track_head_required
def create_subject(semester_id):
    """Create subject"""
    semester = Semester.query.get_or_404(semester_id)
    track = current_user.headed_track
    
    if semester.academic_year.track_id != track.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.track_management'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '').strip()
        total_cm = request.form.get('total_cm', type=int, default=0)
        total_td = request.form.get('total_td', type=int, default=0)
        total_tp = request.form.get('total_tp', type=int, default=0)
        
        if not name or not code:
            flash('Le nom et le code sont obligatoires.', 'danger')
            return render_template('teacher/subject_form.html', semester=semester, track=track)
        
        subject = Subject(
            name=name,
            code=code,
            description=description,
            semester_id=semester_id,
            total_cm=total_cm,
            total_td=total_td,
            total_tp=total_tp
        )
        db.session.add(subject)
        db.session.commit()
        
        flash(f'Matière "{name}" créée avec succès!', 'success')
        return redirect(url_for('teacher.track_management'))
    
    return render_template('teacher/subject_form.html', semester=semester, track=track)


@teacher_bp.route('/track/subject/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@track_head_required
def edit_subject(id):
    """Edit subject"""
    subject = Subject.query.get_or_404(id)
    track = current_user.headed_track
    
    if subject.semester.academic_year.track_id != track.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.track_management'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '').strip()
        total_cm = request.form.get('total_cm', type=int, default=0)
        total_td = request.form.get('total_td', type=int, default=0)
        total_tp = request.form.get('total_tp', type=int, default=0)
        
        if not name or not code:
            flash('Le nom et le code sont obligatoires.', 'danger')
            return render_template('teacher/subject_form.html', subject=subject, semester=subject.semester, track=track)
        
        subject.name = name
        subject.code = code
        subject.description = description
        subject.total_cm = total_cm
        subject.total_td = total_td
        subject.total_tp = total_tp
        db.session.commit()
        
        flash('Matière modifiée avec succès!', 'success')
        return redirect(url_for('teacher.track_management'))
    
    return render_template('teacher/subject_form.html', subject=subject, semester=subject.semester, track=track)


@teacher_bp.route('/track/subject/<int:id>/assign', methods=['GET', 'POST'])
@login_required
@track_head_required
def assign_subject_teacher(id):
    """Assign teacher to subject"""
    subject = Subject.query.get_or_404(id)
    track = current_user.headed_track
    
    if subject.semester.academic_year.track_id != track.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.track_management'))
    
    # Get teachers from same department
    teachers = User.query.filter_by(role='teacher', department_id=track.department_id).order_by(User.last_name).all()
    
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id', type=int)
        teaches_cm = 'teaches_cm' in request.form
        teaches_td = 'teaches_td' in request.form
        teaches_tp = 'teaches_tp' in request.form
        
        if not teacher_id:
            flash('Veuillez sélectionner un enseignant.', 'danger')
            return render_template('teacher/assign_subject.html', subject=subject, teachers=teachers, track=track)
        
        # Check if assignment exists
        assignment = TeacherSubjectAssignment.query.filter_by(
            teacher_id=teacher_id,
            subject_id=id
        ).first()
        
        if assignment:
            assignment.teaches_cm = teaches_cm
            assignment.teaches_td = teaches_td
            assignment.teaches_tp = teaches_tp
        else:
            assignment = TeacherSubjectAssignment(
                teacher_id=teacher_id,
                subject_id=id,
                teaches_cm=teaches_cm,
                teaches_td=teaches_td,
                teaches_tp=teaches_tp
            )
            db.session.add(assignment)
        
        db.session.commit()
        flash('Enseignant assigné avec succès!', 'success')
        return redirect(url_for('teacher.track_management'))
    
    return render_template('teacher/assign_subject.html', subject=subject, teachers=teachers, track=track)


# ==================== STUDENT MANAGEMENT ====================

@teacher_bp.route('/track/students')
@login_required
@track_head_required
def track_students():
    """View students in track"""
    track = current_user.headed_track
    students = track.students
    
    return render_template('teacher/track_students.html', track=track, students=students)


@teacher_bp.route('/track/student/create', methods=['GET', 'POST'])
@login_required
@track_head_required
def create_student():
    """Create a new student"""
    track = current_user.headed_track
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        matricule = request.form.get('matricule', '').strip()
        
        if not email or not first_name or not last_name:
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return render_template('teacher/student_form.html', track=track)
        
        if User.query.filter_by(email=email).first():
            flash('Un utilisateur avec cet email existe déjà.', 'danger')
            return render_template('teacher/student_form.html', track=track)
        
        if matricule and User.query.filter_by(matricule=matricule).first():
            flash('Un utilisateur avec ce matricule existe déjà.', 'danger')
            return render_template('teacher/student_form.html', track=track)
        
        student = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            matricule=matricule if matricule else None,
            role='student'
        )
        student.enrolled_tracks.append(track)
        
        db.session.add(student)
        db.session.commit()
        
        # Send password creation email
        try:
            send_password_creation_email(student)
            db.session.commit()
            flash(f'Étudiant "{first_name} {last_name}" créé. Email envoyé!', 'success')
        except Exception as e:
            flash(f'Étudiant créé mais erreur d\'envoi email: {str(e)}', 'warning')
        
        return redirect(url_for('teacher.track_students'))
    
    return render_template('teacher/student_form.html', track=track)


@teacher_bp.route('/track/students/import', methods=['GET', 'POST'])
@login_required
@track_head_required
def import_students():
    """Import students from Excel"""
    track = current_user.headed_track
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Aucun fichier sélectionné.', 'danger')
            return render_template('teacher/import_students.html', track=track)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('Aucun fichier sélectionné.', 'danger')
            return render_template('teacher/import_students.html', track=track)
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('Format de fichier invalide. Utilisez un fichier Excel (.xlsx).', 'danger')
            return render_template('teacher/import_students.html', track=track)
        
        try:
            wb = openpyxl.load_workbook(BytesIO(file.read()))
            ws = wb.active
            
            imported = 0
            errors = []
            
            for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if not row[0]:
                    continue
                
                email = str(row[0]).strip().lower() if row[0] else None
                first_name = str(row[1]).strip() if row[1] else None
                last_name = str(row[2]).strip() if row[2] else None
                
                if not email or not first_name or not last_name:
                    errors.append(f"Ligne {row_num}: données manquantes")
                    continue
                
                if User.query.filter_by(email=email).first():
                    errors.append(f"Ligne {row_num}: email déjà existant ({email})")
                    continue
                
                student = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role='student'
                )
                student.enrolled_tracks.append(track)
                db.session.add(student)
                
                try:
                    send_password_creation_email(student)
                except:
                    pass
                
                imported += 1
            
            db.session.commit()
            
            if imported > 0:
                flash(f'{imported} étudiant(s) importé(s) avec succès!', 'success')
            if errors:
                flash(f'{len(errors)} erreur(s): ' + '; '.join(errors[:3]), 'warning')
            
            return redirect(url_for('teacher.track_students'))
            
        except Exception as e:
            flash(f'Erreur lors de l\'import: {str(e)}', 'danger')
            return render_template('teacher/import_students.html', track=track)
    
    return render_template('teacher/import_students.html', track=track)


# ==================== TRACK STATISTICS ====================

@teacher_bp.route('/track/statistics')
@login_required
@track_head_required
def track_statistics():
    """View track-wide statistics"""
    track = current_user.headed_track
    
    # Get all subjects in track
    subjects = []
    for year in track.academic_years:
        for semester in year.semesters:
            for subject in semester.subjects:
                subjects.append(subject)
    
    # Calculate stats for each student
    students_stats = []
    for student in track.students:
        student_data = {
            'student': student,
            'subjects': [],
            'total_grade': 0,
            'rattrapage_count': 0
        }
        
        total_grade = 0
        subject_count = 0
        
        for subject in subjects:
            is_rattrapage, stats = calculate_rattrapage_status(student.id, subject.id)
            grade = calculate_attendance_grade(student.id, subject.id)
            
            student_data['subjects'].append({
                'subject': subject,
                'grade': grade,
                'is_rattrapage': is_rattrapage
            })
            
            total_grade += grade
            subject_count += 1
            
            if is_rattrapage:
                student_data['rattrapage_count'] += 1
        
        student_data['total_grade'] = round(total_grade / subject_count, 2) if subject_count > 0 else 20
        students_stats.append(student_data)
    
    return render_template('teacher/track_statistics.html',
                          track=track,
                          subjects=subjects,
                          students_stats=students_stats)
