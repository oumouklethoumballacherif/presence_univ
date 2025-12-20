from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from datetime import datetime

from .models import db, User
from .config_local import LocalConfig   # 🔴 IMPORTANT : MySQL ici

login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)

    # 🔐 Load configuration (SECRET_KEY + MySQL)
    app.config.from_object(LocalConfig)

    # 🔌 Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    # 🔐 Flask-Login config
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'

    # 🕒 Inject current datetime into templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow}

    # 👤 User loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 📦 Register blueprints
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.teacher import teacher_bp
    from .routes.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)

    # 🗄️ Create tables + default admin
    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(email='admin@uir.ac.ma').first()
        if not admin:
            admin = User(
                email='admin@uir.ac.ma',
                first_name='Super',
                last_name='Admin',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

    return app
