from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def admin_required(f):
    """Decorator for super admin only routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            flash('Accès non autorisé.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def teacher_required(f):
    """Decorator for teacher routes (includes dept heads and track heads)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('auth.login'))
        if current_user.role != 'teacher':
            flash('Accès réservé aux enseignants.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def dept_head_required(f):
    """Decorator for department head routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_dept_head or not current_user.headed_department:
            flash('Accès réservé aux chefs de département.', 'danger')
            return redirect(url_for('teacher.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def track_head_required(f):
    """Decorator for track (filière) head routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_track_head or not current_user.headed_track:
            flash('Accès réservé aux chefs de filière.', 'danger')
            return redirect(url_for('teacher.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    """Decorator for student routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('auth.login'))
        if current_user.role != 'student':
            flash('Accès réservé aux étudiants.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
