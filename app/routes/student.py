from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import (db, User, Subject, Course, Attendance, AttendanceToken,
                        calculate_rattrapage_status, calculate_attendance_grade)
from app.utils.decorators import student_required
from app.utils.qr_generator import parse_qr_data
from datetime import datetime

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    """Student dashboard with subjects by semester"""
    # Get student's enrolled tracks
    tracks = current_user.enrolled_tracks
    
    # Organize subjects by track and semester
    tracks_data = []
    for track in tracks:
        track_data = {
            'track': track,
            'years': []
        }
        
        for year in track.academic_years:
            year_data = {
                'year': year,
                'semesters': []
            }
            
            for semester in year.semesters:
                semester_data = {
                    'semester': semester,
                    'subjects': []
                }
                
                for subject in semester.subjects:
                    is_rattrapage, stats = calculate_rattrapage_status(current_user.id, subject.id)
                    grade = calculate_attendance_grade(current_user.id, subject.id)
                    
                    # Count completed sessions
                    completed_courses = Course.query.filter_by(
                        subject_id=subject.id,
                        status='completed'
                    ).count()
                    
                    # Count presences
                    presences = Attendance.query.join(Course).filter(
                        Course.subject_id == subject.id,
                        Attendance.student_id == current_user.id,
                        Attendance.status == 'present'
                    ).count()
                    
                    semester_data['subjects'].append({
                        'subject': subject,
                        'completed_sessions': completed_courses,
                        'presences': presences,
                        'is_rattrapage': is_rattrapage,
                        'grade': grade
                    })
                
                year_data['semesters'].append(semester_data)
            track_data['years'].append(year_data)
        tracks_data.append(track_data)
    
    return render_template('student/dashboard.html', tracks_data=tracks_data)


@student_bp.route('/subject/<int:id>')
@login_required
@student_required
def subject_detail(id):
    """View detailed attendance for a subject"""
    subject = Subject.query.get_or_404(id)
    
    # Verify student is enrolled in this track
    track = subject.semester.academic_year.track
    if track not in current_user.enrolled_tracks:
        flash('Vous n\'êtes pas inscrit à cette filière.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Get all courses for this subject
    courses = Course.query.filter_by(subject_id=id).order_by(Course.created_at).all()
    
    # Calculate stats
    completed_cm = 0
    completed_td = 0
    completed_tp = 0
    present_cm = 0
    present_td = 0
    present_tp = 0
    absent_cm = 0
    absent_td = 0
    absent_tp = 0
    
    courses_data = []
    for course in courses:
        attendance = Attendance.query.filter_by(
            course_id=course.id,
            student_id=current_user.id
        ).first()
        
        courses_data.append({
            'course': course,
            'attendance': attendance
        })
        
        if course.status == 'completed':
            if course.course_type == 'CM':
                completed_cm += 1
                if attendance and attendance.status == 'present':
                    present_cm += 1
                else:
                    absent_cm += 1
            elif course.course_type == 'TD':
                completed_td += 1
                if attendance and attendance.status == 'present':
                    present_td += 1
                else:
                    absent_td += 1
            elif course.course_type == 'TP':
                completed_tp += 1
                if attendance and attendance.status == 'present':
                    present_tp += 1
                else:
                    absent_tp += 1
    
    is_rattrapage, rattrapage_stats = calculate_rattrapage_status(current_user.id, id)
    grade = calculate_attendance_grade(current_user.id, id)
    
    stats = {
        'total_cm': subject.total_cm,
        'total_td': subject.total_td,
        'total_tp': subject.total_tp,
        'completed_cm': completed_cm,
        'completed_td': completed_td,
        'completed_tp': completed_tp,
        'present_cm': present_cm,
        'present_td': present_td,
        'present_tp': present_tp,
        'absent_cm': absent_cm,
        'absent_td': absent_td,
        'absent_tp': absent_tp,
        'remaining_cm': subject.total_cm - completed_cm,
        'remaining_td': subject.total_td - completed_td,
        'remaining_tp': subject.total_tp - completed_tp,
        'is_rattrapage': is_rattrapage,
        'grade': grade
    }
    
    return render_template('student/subject_detail.html',
                          subject=subject,
                          courses_data=courses_data,
                          stats=stats,
                          rattrapage_stats=rattrapage_stats)


@student_bp.route('/scan')
@login_required
@student_required
def scan():
    """QR code scanner page"""
    return render_template('student/scan.html')


@student_bp.route('/attendance', methods=['POST'])
@login_required
@student_required
def record_attendance():
    """Record attendance from QR code scan"""
    qr_data = request.json.get('qr_data', '')
    
    if not qr_data:
        return jsonify({'success': False, 'message': 'Données QR invalides'}), 400
    
    # Parse QR data
    parsed = parse_qr_data(qr_data)
    if not parsed:
        return jsonify({'success': False, 'message': 'Format QR invalide'}), 400
    
    course_id, token, timestamp = parsed
    
    # Get course
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'success': False, 'message': 'Séance non trouvée'}), 404
    
    # Check if course is active
    if course.status != 'active':
        return jsonify({'success': False, 'message': 'Cette séance n\'est pas active'}), 400
    
    # Verify token using AttendanceToken table
    attendance_token = AttendanceToken.query.filter_by(
        course_id=course_id,
        token=token
    ).first()
    
    if not attendance_token or not attendance_token.is_valid():
        return jsonify({'success': False, 'message': 'QR code expiré. Veuillez rescanner.'}), 400
    
    # Check if student is enrolled in the track
    track = course.subject.semester.academic_year.track
    if track not in current_user.enrolled_tracks:
        return jsonify({'success': False, 'message': 'Vous n\'êtes pas inscrit à cette filière'}), 403
    
    # Get or create attendance record
    attendance = Attendance.query.filter_by(
        course_id=course_id,
        student_id=current_user.id
    ).first()
    
    if not attendance:
        attendance = Attendance(
            course_id=course_id,
            student_id=current_user.id
        )
        db.session.add(attendance)
    
    if attendance.status == 'present':
        return jsonify({
            'success': True, 
            'message': 'Présence déjà enregistrée!',
            'already_recorded': True
        })
    
    attendance.scanned_at = datetime.utcnow()
    
    # Calculate status based on time (Late if > 20 mins)
    if course.started_at:
        delta = (attendance.scanned_at - course.started_at).total_seconds()
        if delta > 1200: # 20 minutes
            attendance.status = 'late'
        else:
            attendance.status = 'present'
    else:
        attendance.status = 'present'
        
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Présence enregistrée avec succès!',
        'course': {
            'subject': course.subject.name,
            'type': course.course_type,
            'title': course.title
        }
    })


@student_bp.route('/profile')
@login_required
@student_required
def profile():
    """Student profile page"""
    return render_template('student/profile.html')
