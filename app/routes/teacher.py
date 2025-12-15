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
            
        # Calculate session progress
        # Count sessions created by this teacher for this subject
        sessions_count = {
            'CM': Course.query.filter_by(teacher_id=current_user.id, subject_id=subject.id, course_type='CM').count(),
            'TD': Course.query.filter_by(teacher_id=current_user.id, subject_id=subject.id, course_type='TD').count(),
            'TP': Course.query.filter_by(teacher_id=current_user.id, subject_id=subject.id, course_type='TP').count()
        }

        subjects.append({
            'subject': subject,
            'assignment': assignment,
            'track': track,
            'academic_year': year,
            'semester': semester,
            'progress': sessions_count
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
    
    # Get track students filtered by current year level
    track = course.subject.semester.academic_year.track
    academic_year_id = course.subject.semester.academic_year_id
    students = [s for s in track.students if s.current_year_id == academic_year_id]
    
    # Get attendance data
    attendance_data = []
    for student in students:
        attendance = Attendance.query.filter_by(
            course_id=course.id,
            student_id=student.id
        ).first()
        
        delay = None
        if attendance and attendance.status == 'late' and attendance.scanned_at and course.started_at:
            delta = attendance.scanned_at - course.started_at
            # delay in minutes
            delay = int(max(0, delta.total_seconds() // 60))

        attendance_data.append({
            'student': student,
            'attendance': attendance,
            'delay': delay
        })

    late_count = sum(1 for item in attendance_data if item['attendance'] and item['attendance'].status == 'late')
    
    return render_template('teacher/course_detail.html', 
                          course=course,
                          attendance_data=attendance_data,
                          late_count=late_count)


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
    
    # Create attendance records for all students currently in this year
    track = course.subject.semester.academic_year.track
    academic_year_id = course.subject.semester.academic_year_id
    
    # Filter students who are actually in this academic year
    relevant_students = [s for s in track.students if s.current_year_id == academic_year_id]

    for student in relevant_students:
        # Check if record already exists to avoid IntegrityError (e.g. if manually marked before start)
        existing_attendance = Attendance.query.filter_by(
            course_id=course.id,
            student_id=student.id
        ).first()
        
        if not existing_attendance:
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
    
    # Count students: total and present
    track = course.subject.semester.academic_year.track
    academic_year_id = course.subject.semester.academic_year_id
    total_students = len([s for s in track.students if s.current_year_id == academic_year_id])
    present_students = Attendance.query.filter_by(
        course_id=course.id,
        status='present'
    ).count()
    
    return render_template('teacher/qr_display.html', 
                         course=course, 
                         qr_image=qr_image,
                         total_students=total_students,
                         present_students=present_students)


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
    
    # Count students: total and present
    track = course.subject.semester.academic_year.track
    total_students = len(track.students)
    present_students = Attendance.query.filter_by(
        course_id=course.id,
        status='present'
    ).count()
    
    return jsonify({
        'qr_image': qr_image,
        'token': new_token.token,
        'expires_at': new_token.expires_at.isoformat(),
        'present_students': present_students,
        'total_students': total_students
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



@teacher_bp.route('/course/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_course(id):
    """Edit an existing course session"""
    course = Course.query.get_or_404(id)
    
    # Verify ownership
    if course.teacher_id != current_user.id:
        flash('Vous ne pouvez pas modifier ce cours.', 'danger')
        return redirect(url_for('teacher.courses'))
        
    # Verify status (can only edit pending courses usually)
    if course.status != 'pending':
        flash('Impossible de modifier un cours déjà commencé ou terminé.', 'warning')
        return redirect(url_for('teacher.course_detail', id=id))

    subject = course.subject
    assignment = TeacherSubjectAssignment.query.filter_by(
        teacher_id=current_user.id,
        subject_id=subject.id
    ).first()

    if request.method == 'POST':
        course_type = request.form.get('course_type')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        
        if course_type not in ['CM', 'TD', 'TP']:
            flash('Type de cours invalide.', 'danger')
            return render_template('teacher/course_form.html', subject=subject, assignment=assignment, course=course)
            
        # Check permissions if type changed
        if course_type != course.course_type:
            can_teach = (
                (course_type == 'CM' and assignment.teaches_cm) or
                (course_type == 'TD' and assignment.teaches_td) or
                (course_type == 'TP' and assignment.teaches_tp)
            )
            if not can_teach:
                flash(f'Vous n\'êtes pas autorisé à enseigner les {course_type}.', 'danger')
                return render_template('teacher/course_form.html', subject=subject, assignment=assignment, course=course)
        
        course.course_type = course_type
        course.title = title or f"{subject.name} - {course_type}"
        course.description = description
        
        db.session.commit()
        flash('Séance modifiée avec succès!', 'success')
        return redirect(url_for('teacher.courses'))

    return render_template('teacher/course_form.html', subject=subject, assignment=assignment, course=course)


@teacher_bp.route('/course/delete/<int:id>', methods=['POST'])
@login_required
@teacher_required
def delete_course(id):
    """Delete a course session"""
    course = Course.query.get_or_404(id)
    
    if course.teacher_id != current_user.id:
        flash('Action non autorisée.', 'danger')
        return redirect(url_for('teacher.courses'))
        
    if course.status != 'pending':
        flash('Impossible de supprimer un cours déjà commencé.', 'danger')
        return redirect(url_for('teacher.courses'))
        
    db.session.delete(course)
    db.session.commit()
    flash('Séance supprimée.', 'success')
    return redirect(url_for('teacher.courses'))


@teacher_bp.route('/courses/bulk-delete', methods=['POST'])
@login_required
@teacher_required
def bulk_delete_courses():
    """Delete multiple course sessions"""
    course_ids = request.form.getlist('course_ids')
    
    if not course_ids:
        flash('Aucune séance sélectionnée.', 'warning')
        return redirect(url_for('teacher.courses'))
        
    deleted_count = 0
    for course_id in course_ids:
        course = Course.query.get(course_id)
        if course and course.teacher_id == current_user.id and course.status == 'pending':
            db.session.delete(course)
            deleted_count += 1
            
    db.session.commit()
    
    if deleted_count > 0:
        flash(f'{deleted_count} séances supprimées avec succès.', 'success')
    else:
        flash('Aucune séance n\'a pu être supprimée (déjà commencées ou non autorisées).', 'warning')
        
    return redirect(url_for('teacher.courses'))


@teacher_bp.route('/course/<int:course_id>/attendance/<int:student_id>/update', methods=['POST'])
@login_required
@teacher_required
def update_course_attendance(course_id, student_id):
    """Update attendance status for a specific student in a course"""
    course = Course.query.get_or_404(course_id)
    
    if course.teacher_id != current_user.id:
        return jsonify({'success': False, 'message': 'Accès non autorisé'}), 403
    
    status = request.form.get('status')
    if status not in ['present', 'absent', 'late']:
        return jsonify({'success': False, 'message': 'Statut invalide'}), 400
        
    attendance = Attendance.query.filter_by(
        course_id=course_id,
        student_id=student_id
    ).first()
    
    if not attendance:
        attendance = Attendance(
            course_id=course_id,
            student_id=student_id,
            status=status
        )
        db.session.add(attendance)
    else:
        attendance.status = status
        # If manually marked, maybe update scanned_at? 
        # If marking present/late manualy, we could set scanned_at to now if None
        if (status == 'present' or status == 'late') and not attendance.scanned_at:
            attendance.scanned_at = datetime.utcnow()
        elif status == 'absent':
             attendance.scanned_at = None
        
    db.session.commit()
    return jsonify({'success': True})


# ==================== ATTENDANCE CONSULTATION ====================

@teacher_bp.route('/subject/<int:id>/attendance')
@login_required
@teacher_required
def subject_attendance(id):
    """View attendance for a subject"""
    subject = Subject.query.get_or_404(id)
    
    # Permission Check: Assigned Teacher OR Track Head
    is_assigned = TeacherSubjectAssignment.query.filter_by(
        teacher_id=current_user.id,
        subject_id=id
    ).first()
    
    is_track_head = (current_user.is_track_head and 
                    current_user.headed_track.id == subject.semester.academic_year.track_id)
    
    if not is_assigned and not is_track_head:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    # Get completed courses
    courses = Course.query.filter_by(
        subject_id=id,
        status='completed'
    ).order_by(Course.started_at.desc()).all()
    
    # Get students and their attendance
    track = subject.semester.academic_year.track
    academic_year_id = subject.semester.academic_year_id
    students_data = []
    
    # Filter students by current year level
    relevant_students = [s for s in track.students if s.current_year_id == academic_year_id]
    
    for student in relevant_students:
        student_attendance = {
            'student': student,
            'courses': []
        }
        
        total = 0
        present = 0
        
        # Rate vars (CM/TD)
        cm_td_total = 0
        cm_td_points = 0

        for course in courses:
            attendance = Attendance.query.filter_by(
                course_id=course.id,
                student_id=student.id
            ).first()
            
            if attendance:
                total += 1
                if attendance.status == 'present':
                    present += 1
            
            # CM/TD Rate Logic (counts late as 0.5)
            if course.course_type in ['CM', 'TD']:
                cm_td_total += 1
                if attendance:
                    if attendance.status == 'present':
                        cm_td_points += 1
                    elif attendance.status == 'late':
                        cm_td_points += 0.5
            
            student_attendance['courses'].append({
                'course': course,
                'attendance': attendance
            })
        
        is_rattrapage, stats = calculate_rattrapage_status(student.id, id)
        grade = calculate_attendance_grade(student.id, id)
        
        student_attendance['total'] = total
        student_attendance['present'] = present
        student_attendance['rate'] = (cm_td_points / cm_td_total * 100) if cm_td_total > 0 else 100
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
        
        if not name:
            flash('Le nom est obligatoire.', 'danger')
            return render_template('teacher/subject_form.html', semester=semester, track=track)
        
        # Auto-generate code if empty
        if not code:
            # 1. Track Abbreviation
            track_words = track.name.upper().split()
            abbrev = track_words[0][:4] if track_words else 'GENI'
            for word in track_words:
                if word not in ['GENIE', 'MASTER', 'LICENCE', 'DOCTORAT']:
                    abbrev = word[:4]
                    break
            
            # 2. Level
            level_initial = track.level[0].upper() if track.level else 'L'
            year_order = semester.academic_year.order
            level_code = f"{level_initial}{year_order}"
            
            # 3. Number
            existing_count = 0
            for sem in semester.academic_year.semesters:
                existing_count += len(sem.subjects)
            number = existing_count + 1
            
            code = f"{abbrev}-{level_code}-{number:02d}"

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
        
        if not name:
            flash('Le nom est obligatoire.', 'danger')
            return render_template('teacher/subject_form.html', subject=subject, semester=subject.semester, track=track)
        
        # Keep existing code if empty
        if not code:
            code = subject.code

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
    
    # Check for edit mode
    edit_teacher_id = request.args.get('edit_teacher_id', type=int)
    current_assignment = None
    if edit_teacher_id:
        current_assignment = TeacherSubjectAssignment.query.filter_by(
            teacher_id=edit_teacher_id,
            subject_id=id
        ).first()

    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id', type=int)
        teaches_cm = 'teaches_cm' in request.form
        teaches_td = 'teaches_td' in request.form
        teaches_tp = 'teaches_tp' in request.form
        
        if not teacher_id:
            flash('Veuillez sélectionner un enseignant.', 'danger')
            return render_template('teacher/assign_subject.html', subject=subject, teachers=teachers, track=track, current_assignment=current_assignment)
        
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
        # Redirect simply clears the query params
        return redirect(url_for('teacher.assign_subject_teacher', id=id))
    
    return render_template('teacher/assign_subject.html', subject=subject, teachers=teachers, track=track, current_assignment=current_assignment)


@teacher_bp.route('/track/subject/unassign/<int:subject_id>/<int:teacher_id>', methods=['POST'])
@login_required
@track_head_required
def unassign_subject_teacher(subject_id, teacher_id):
    """Unassign teacher from subject"""
    subject = Subject.query.get_or_404(subject_id)
    track = current_user.headed_track
    
    if subject.semester.academic_year.track_id != track.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.track_management'))
    
    assignment = TeacherSubjectAssignment.query.filter_by(
        subject_id=subject_id,
        teacher_id=teacher_id
    ).first_or_404()
    
    db.session.delete(assignment)
    db.session.commit()
    
    flash('Enseignant retiré avec succès.', 'success')
    return redirect(url_for('teacher.assign_subject_teacher', id=subject_id))


@teacher_bp.route('/track/subject/unassign_bulk/<int:subject_id>', methods=['POST'])
@login_required
@track_head_required
def unassign_subject_teachers_bulk(subject_id):
    """Unassign multiple teachers from subject"""
    subject = Subject.query.get_or_404(subject_id)
    track = current_user.headed_track
    
    if subject.semester.academic_year.track_id != track.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('teacher.track_management'))
    
    teacher_ids = request.form.getlist('teacher_ids')
    
    if teacher_ids:
        TeacherSubjectAssignment.query.filter(
            TeacherSubjectAssignment.subject_id == subject_id,
            TeacherSubjectAssignment.teacher_id.in_(teacher_ids)
        ).delete(synchronize_session=False)
        
        db.session.commit()
        flash(f'{len(teacher_ids)} enseignant(s) retiré(s) avec succès.', 'success')
    else:
        flash('Aucun enseignant sélectionné.', 'warning')
        
    return redirect(url_for('teacher.assign_subject_teacher', id=subject_id))


# ==================== STUDENT MANAGEMENT ====================

@teacher_bp.route('/track/students')
@login_required
@track_head_required
def track_students():
    """View students in track"""
    track = current_user.headed_track
    search = request.args.get('search', '').strip()
    
    query = User.query.filter(User.enrolled_tracks.any(id=track.id))
    
    if search:
        query = query.filter(
            (User.first_name.ilike(f'%{search}%')) |
            (User.last_name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%')) |
            (User.matricule.ilike(f'%{search}%'))
        )
        
    students = query.order_by(User.last_name, User.first_name).all()
    
    return render_template('teacher/track_students.html', track=track, students=students, search=search)


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
        
        # Assign to first academic year by default
        first_year = AcademicYear.query.filter_by(track_id=track.id).order_by(AcademicYear.order).first()
        if first_year:
            student.current_year = first_year
        
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


@teacher_bp.route('/track/student/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@track_head_required
def edit_student(id):
    """Edit a student"""
    student = User.query.get_or_404(id)
    track = current_user.headed_track
    
    # Security check
    if track not in student.enrolled_tracks:
        flash('Étudiant non trouvé dans cette filière.', 'danger')
        return redirect(url_for('teacher.track_students'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        matricule = request.form.get('matricule', '').strip()
        
        if not email or not first_name or not last_name:
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return render_template('teacher/student_form.html', student=student, track=track)
        
        # Check email uniqueness
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != student.id:
            flash('Un utilisateur avec cet email existe déjà.', 'danger')
            return render_template('teacher/student_form.html', student=student, track=track)
            
        # Check matricule uniqueness
        if matricule:
            existing_mat = User.query.filter_by(matricule=matricule).first()
            if existing_mat and existing_mat.id != student.id:
                flash('Un utilisateur avec ce matricule existe déjà.', 'danger')
                return render_template('teacher/student_form.html', student=student, track=track)
        
        student.email = email
        student.first_name = first_name
        student.last_name = last_name
        student.matricule = matricule if matricule else None
        
        db.session.commit()
        flash('Informations étudiant mises à jour.', 'success')
        return redirect(url_for('teacher.track_students'))
        
    return render_template('teacher/student_form.html', student=student, track=track)


@teacher_bp.route('/track/students/delete_bulk', methods=['POST'])
@login_required
@track_head_required
def delete_students_bulk():
    """Delete multiple students"""
    track = current_user.headed_track
    student_ids = request.form.getlist('student_ids')
    
    if student_ids:
        # Get students to delete
        students = User.query.filter(
            User.id.in_(student_ids),
            User.role == 'student'
        ).all()
        
        deleted_count = 0
        for student in students:
            # Verify student is in this track
            if track in student.enrolled_tracks:
                db.session.delete(student)
                deleted_count += 1
                
        db.session.commit()
        
        if deleted_count > 0:
            flash(f'{deleted_count} étudiant(s) supprimé(s).', 'success')
        else:
            flash('Aucun étudiant supprimé.', 'warning')
    else:
        flash('Aucun étudiant sélectionné.', 'warning')
        
    return redirect(url_for('teacher.track_students'))


# ==================== TRACK STATISTICS ====================

@teacher_bp.route('/track/statistics')
@login_required
@teacher_required
def track_statistics():
    """View track-wide statistics and external subject stats"""
    # Permission Check
    if not current_user.is_track_head and not current_user.is_dept_head:
        flash('Accès non autorisé. Rôle de chef de filière ou département requis.', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # 1. Identify all relevant subjects
    track_subjects = set()
    
    # Scope A: Department Head (See EVERYTHING in Dept)
    if current_user.is_dept_head:
        dept = current_user.headed_department
        if dept:
            tracks = Track.query.filter_by(department_id=dept.id).all()
            for t in tracks:
                for year in t.academic_years:
                    for semester in year.semesters:
                        for subject in semester.subjects:
                            track_subjects.add(subject)
                            
    # Scope B: Track Head (See their Track)
    if current_user.is_track_head:
        track = current_user.headed_track
        if track:
            for year in track.academic_years:
                for semester in year.semesters:
                    for subject in semester.subjects:
                        track_subjects.add(subject)
                
    # C. Subjects I teach (always include)
    my_assignments = TeacherSubjectAssignment.query.filter_by(teacher_id=current_user.id).all()
    my_subjects = set(a.subject for a in my_assignments)
    
    # Merge unique
    all_subjects = list(track_subjects.union(my_subjects))
    all_subjects.sort(key=lambda x: x.name)
    
    # Define School Year Start (Assuming Sept 1st)
    now = datetime.utcnow()
    start_year = now.year if now.month >= 9 else now.year - 1
    school_year_start = datetime(start_year, 9, 1)

    # 2. Calculate Stats per Subject
    subjects_stats_data = []
    
    for subject in all_subjects:
        # Get completed courses for CURRENT SCHOOL YEAR
        completed_courses = Course.query.filter(
            Course.subject_id == subject.id, 
            Course.status == 'completed',
            Course.scheduled_date >= school_year_start
        ).all()
        sessions_count = len(completed_courses)
        
        subj_track = subject.semester.academic_year.track
        subj_year_id = subject.semester.academic_year_id
        
        # Filter students who are CURRENTLY in this level (L1, L2, etc.)
        relevant_students = [s for s in subj_track.students if s.current_year_id == subj_year_id]
        students_count = len(relevant_students)
        
        if sessions_count == 0 or students_count == 0:
            rate = 0
        else:
            # Query Logic for Rate
            # We want: Total Present records / Total Possible records
            total_possible = students_count * sessions_count
            
            # Count present records ONLY for current year courses
            total_present = Attendance.query.join(Course).filter(
                Course.subject_id == subject.id,
                Course.status == 'completed',
                Course.scheduled_date >= school_year_start,
                Attendance.status == 'present'
            ).count()
            
            rate = (total_present / total_possible) * 100
        
        subjects_stats_data.append({
            'subject': subject,
            'sessions_count': sessions_count,
            'students_count': students_count,
            'rate': round(rate, 1),
            'track_name': subj_track.name,
            'is_in_my_track': subject in track_subjects,
            'is_taught_by_me': subject in my_subjects
        })
    
    # 3. Calculate Stats per Student
    # Shown only if the user heads a specific track
    # 3. Calculate Stats per Student
    students_stats = []
    target_tracks = {}
    focus_track = current_user.headed_track if current_user.is_track_head else None
    
    if current_user.is_track_head and current_user.headed_track:
        target_tracks[current_user.headed_track.id] = current_user.headed_track
        
    if current_user.is_dept_head and current_user.headed_department:
        dept_tracks = Track.query.filter_by(department_id=current_user.headed_department.id).all()
        for t in dept_tracks:
            target_tracks[t.id] = t
            
    # Iterate over each relevant track
    for track in target_tracks.values():
        # Get subjects specifically for this track
        track_subjects = []
        for year in track.academic_years:
            for semester in year.semesters:
                for subject in semester.subjects:
                    track_subjects.append(subject)
    
        for student in track.students:
            student_data = {
                'student': student,
                'total_grade': 0,
                'rattrapage_count': 0,
                'track_name': track.name,
                'year_name': student.current_year.name if student.current_year else "Diplômé"
            }
            
            total_grade = 0
            subject_count = 0
            
            for subject in track_subjects:
                # Only count subjects that match the student's current year (if they have one)
                # Optimization: filter track_subjects earlier or here?
                # Actually, precise calculation:
                # If student is L1, only L1 subjects count for their average/rattrapage?
                # YES. Mixing L1 subjects for an L2 student is wrong.
                
                # Filter subject by student's year
                if student.current_year_id and subject.semester.academic_year_id != student.current_year_id:
                    continue
                    
                is_rattrapage, stats = calculate_rattrapage_status(student.id, subject.id)
                grade = calculate_attendance_grade(student.id, subject.id)
                
                total_grade += grade
                subject_count += 1
                
                if is_rattrapage:
                    student_data['rattrapage_count'] += 1
            
            student_data['total_grade'] = round(total_grade / subject_count, 2) if subject_count > 0 else 20
            students_stats.append(student_data)
            
    students_stats.sort(key=lambda x: (-x['rattrapage_count'], x['total_grade']))
    
    return render_template('teacher/track_statistics.html',
                          track=focus_track,
                          subjects_stats=subjects_stats_data,
                          students_stats=students_stats)
