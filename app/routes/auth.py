from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Course
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    """Redirect to appropriate dashboard based on role"""
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher.dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(email=email).first()
        
        if user is None:
            flash('Email ou mot de passe incorrect.', 'danger')
            return render_template('auth/login.html')
        
        if not user.password_hash:
            flash('Veuillez d\'abord créer votre mot de passe via le lien envoyé par email.', 'warning')
            return render_template('auth/login.html')
        
        if not user.check_password(password):
            flash('Email ou mot de passe incorrect.', 'danger')
            return render_template('auth/login.html')
        
        if not user.is_active:
            flash('Votre compte a été désactivé.', 'danger')
            return render_template('auth/login.html')
        
        login_user(user, remember=remember)
        flash(f'Bienvenue, {user.first_name}!', 'success')
        
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        return redirect(url_for('auth.index'))
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    # Auto-complete active courses for teacher
    if current_user.role == 'teacher':
        active_courses = Course.query.filter_by(
            teacher_id=current_user.id,
            status='active'
        ).all()
        
        for course in active_courses:
            course.status = 'completed'
            course.ended_at = datetime.utcnow()
        
        if active_courses:
            db.session.commit()
            # Optional: flash message? User asked for silent behavior or just "it must be broken/ended".
            # flash(f'{len(active_courses)} cours actifs ont été terminés.', 'info')

    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/create-password/<token>', methods=['GET', 'POST'])
def create_password(token):
    """Create password for new account"""
    user = User.query.filter_by(token=token).first()
    
    if not user or not user.verify_token():
        flash('Le lien est invalide ou a expiré.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        
        if len(password) < 8:
            flash('Le mot de passe doit contenir au moins 8 caractères.', 'danger')
            return render_template('auth/create_password.html', token=token)
        
        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('auth/create_password.html', token=token)
        
        user.set_password(password)
        user.clear_token()
        db.session.commit()
        
        flash('Mot de passe créé avec succès! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/create_password.html', token=token, user=user)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    
    if request.method == 'POST':
        from app.utils.email import send_password_reset_email
        
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if user:
            send_password_reset_email(user)
            db.session.commit()
        
        # Always show success message to prevent email enumeration
        flash('Si un compte existe avec cet email, vous recevrez un lien de réinitialisation.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    
    user = User.query.filter_by(token=token).first()
    
    if not user or not user.verify_token():
        flash('Le lien est invalide ou a expiré.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        
        if len(password) < 8:
            flash('Le mot de passe doit contenir au moins 8 caractères.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        user.set_password(password)
        user.clear_token()
        db.session.commit()
        
        flash('Mot de passe réinitialisé avec succès!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)
