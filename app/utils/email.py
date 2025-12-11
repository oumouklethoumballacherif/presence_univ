from flask import current_app, url_for
from flask_mail import Message
from app import mail
from threading import Thread


def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Error sending email: {e}")


def send_email(subject, recipient, html_body, text_body=None):
    """Send email asynchronously"""
    msg = Message(
        subject=subject,
        recipients=[recipient],
        html=html_body,
        body=text_body or html_body
    )
    # Send async
    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg)
    ).start()


def send_password_creation_email(user):
    """Send email with link to create password"""
    token = user.generate_token()
    reset_url = url_for('auth.create_password', token=token, _external=True)
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #F2F2F2; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #163A59;">UIR - Système de Présence</h1>
            </div>
            <h2 style="color: #5F7340;">Bienvenue {user.first_name} {user.last_name}!</h2>
            <p>Votre compte a été créé sur la plateforme de gestion de présence de l'UIR.</p>
            <p>Cliquez sur le bouton ci-dessous pour créer votre mot de passe :</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background-color: #163A59; color: white; padding: 15px 30px; 
                          text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Créer mon mot de passe
                </a>
            </div>
            <p style="color: #666; font-size: 12px;">
                Ce lien expire dans 24 heures.<br>
                Si vous n'avez pas demandé ce compte, ignorez cet email.
            </p>
        </div>
    </body>
    </html>
    """
    
    send_email(
        subject="[UIR] Créez votre mot de passe",
        recipient=user.email,
        html_body=html_body
    )


def send_password_reset_email(user):
    """Send password reset email"""
    token = user.generate_token()
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #F2F2F2; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #163A59;">UIR - Système de Présence</h1>
            </div>
            <h2 style="color: #5F7340;">Réinitialisation du mot de passe</h2>
            <p>Bonjour {user.first_name},</p>
            <p>Vous avez demandé la réinitialisation de votre mot de passe.</p>
            <p>Cliquez sur le bouton ci-dessous pour définir un nouveau mot de passe :</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background-color: #163A59; color: white; padding: 15px 30px; 
                          text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Réinitialiser mon mot de passe
                </a>
            </div>
            <p style="color: #666; font-size: 12px;">
                Ce lien expire dans 24 heures.<br>
                Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
            </p>
        </div>
    </body>
    </html>
    """
    
    send_email(
        subject="[UIR] Réinitialisation de votre mot de passe",
        recipient=user.email,
        html_body=html_body
    )
