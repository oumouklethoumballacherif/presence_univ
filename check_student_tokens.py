"""Script pour vérifier les tokens des étudiants"""
from app import create_app
from app.models import db, User
from datetime import datetime

app = create_app()

with app.app_context():
    students = User.query.filter_by(role='student').all()
    
    print("=" * 80)
    print("VÉRIFICATION DES TOKENS DES ÉTUDIANTS")
    print("=" * 80)
    print()
    
    if not students:
        print("⚠️  Aucun étudiant trouvé dans la base de données")
    else:
        print(f"📊 Total étudiants: {len(students)}\n")
        
        for student in students:
            print(f"👤 {student.full_name} ({student.email})")
            print(f"   Matricule: {student.matricule or 'Non défini'}")
            print(f"   Token: {student.token[:20] + '...' if student.token else '❌ AUCUN TOKEN'}")
            
            if student.token_expiry:
                now = datetime.utcnow()
                if now < student.token_expiry:
                    remaining = student.token_expiry - now
                    hours = int(remaining.total_seconds() / 3600)
                    print(f"   Expiration: ✅ Valide (encore {hours}h)")
                else:
                    print(f"   Expiration: ❌ Expiré le {student.token_expiry}")
            else:
                print(f"   Expiration: ❌ Aucune date d'expiration")
            
            print(f"   Mot de passe défini: {'✅ Oui' if student.password_hash else '❌ Non'}")
            print()
    
    print("=" * 80)
