
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
        # Allow viewing but maybe disabled? For now redirect.
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
