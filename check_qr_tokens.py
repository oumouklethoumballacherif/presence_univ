"""Script de diagnostic pour les tokens QR"""
from app import create_app
from app.models import db, Course, AttendanceToken
from datetime import datetime

app = create_app()

with app.app_context():
    print("=" * 80)
    print("DIAGNOSTIC DES TOKENS QR")
    print("=" * 80)
    print()
    
    # Chercher les cours actifs
    active_courses = Course.query.filter_by(status='active').all()
    
    if not active_courses:
        print("ℹ️  Aucun cours actif trouvé")
    else:
        print(f"📊 {len(active_courses)} cours actif(s) trouvé(s)\n")
        
        for course in active_courses:
            print(f"📚 Cours: {course.subject.name} - {course.course_type}")
            print(f"   ID: {course.id}")
            print(f"   Statut: {course.status}")
            print(f"   Démarré: {course.started_at}")
            
            # Vérifier les tokens AttendanceToken
            tokens = AttendanceToken.query.filter_by(course_id=course.id).order_by(
                AttendanceToken.created_at.desc()
            ).all()
            
            if not tokens:
                print(f"   ❌ AUCUN token AttendanceToken trouvé !")
            else:
                print(f"   ✅ {len(tokens)} token(s) AttendanceToken:")
                for i, token in enumerate(tokens[:3], 1):  # Montrer les 3 plus récents
                    now = datetime.utcnow()
                    is_valid = token.is_valid()
                    validity_str = "VALIDE" if is_valid else "EXPIRÉ"
                    time_diff = (now - token.created_at).total_seconds()
                    
                    print(f"      {i}. {token.token[:20]}... ({validity_str})")
                    print(f"         Créé il y a {int(time_diff)}s")
                    print(f"         Expire: {token.expires_at}")
            
            # Vérifier l'ancien système (course.qr_token)
            if course.qr_token:
                print(f"   ⚠️  Ancien qr_token trouvé: {course.qr_token[:20]}...")
                print(f"      (Non utilisé par le nouveau système)")
            
            print()
    
    print("=" * 80)
    print("💡 INFO: Le système utilise maintenant la table AttendanceToken")
    print("   Les tokens sont régénérés toutes les 15 secondes")
    print("=" * 80)
