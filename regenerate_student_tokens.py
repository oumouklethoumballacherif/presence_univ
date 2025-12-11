"""Script pour régénérer les tokens pour les étudiants sans mot de passe"""
from app import create_app
from app.models import db, User
from app.utils.email import send_password_creation_email

app = create_app()

with app.app_context():
    # Trouver tous les étudiants sans mot de passe
    students_without_password = User.query.filter_by(
        role='student',
        password_hash=None
    ).all()
    
    print("=" * 80)
    print("RÉGÉNÉRATION DES TOKENS POUR ÉTUDIANTS SANS MOT DE PASSE")
    print("=" * 80)
    print()
    
    if not students_without_password:
        print("✅ Tous les étudiants ont déjà un mot de passe défini")
    else:
        print(f"📊 {len(students_without_password)} étudiant(s) sans mot de passe trouvé(s)\n")
        
        success_count = 0
        error_count = 0
        
        for student in students_without_password:
            try:
                print(f"🔄 Traitement de {student.full_name} ({student.email})...")
                
                # Générer un nouveau token et envoyer l'email
                send_password_creation_email(student)
                
                success_count += 1
                print(f"   ✅ Token régénéré et email envoyé")
                
            except Exception as e:
                error_count += 1
                print(f"   ❌ Erreur: {str(e)}")
            
            print()
        
        print("=" * 80)
        print(f"✅ Terminé : {success_count} succès, {error_count} erreur(s)")
        print("=" * 80)
