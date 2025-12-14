@admin_bp.route('/students/promote', methods=['GET', 'POST'])
@login_required
@admin_required
def promote_students():
    """Promote students to the next academic year"""
    if request.method == 'POST':
        track_id = request.form.get('track_id', type=int)
        track = Track.query.get_or_404(track_id)
        
        # Get all years ordered by orderdesc/asc
        # We need to process from highest to lowest to avoid double promotion if we do simple updates?
        # Actually logic:
        # Get students in track.
        # For each student, get current year order.
        # Find year with order + 1.
        # If exists, update.
        
        promoted_count = 0
        students = User.query.filter(User.enrolled_tracks.any(id=track.id)).all()
        
        # Get years map: {order: year_object}
        years = {y.order: y for y in track.academic_years}
        max_order = max(years.keys()) if years else 0
        
        for student in students:
            if not student.current_year:
                continue
                
            # Ensure student is in this track's year (sanity check)
            if student.current_year.track_id != track.id:
                continue
                
            current_order = student.current_year.order
            next_order = current_order + 1
            
            if next_order in years:
                student.current_year = years[next_order]
                promoted_count += 1
            else:
                # End of track (Graduate?)
                # For now do nothing or log
                pass
        
        db.session.commit()
        flash(f'{promoted_count} étudiants promus vers l\'année supérieure dans la filière {track.name}.', 'success')
        return redirect(url_for('admin.students'))
        
    tracks = Track.query.order_by(Track.name).all()
    return render_template('admin/promote_students.html', tracks=tracks)
