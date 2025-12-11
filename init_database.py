"""Script d'initialisation de la base de données"""
import pymysql
from app import create_app
from app.models import db

def create_database():
    """Crée la base de données si elle n'existe pas"""
    try:
        # Connexion à MySQL sans spécifier la base de données
        connection = pymysql.connect(
            host='localhost',
            port=3306,
            user='root',
            password='MYSQL123'
        )
        
        with connection.cursor() as cursor:
            # Créer la base de données si elle n'existe pas
            cursor.execute("CREATE DATABASE IF NOT EXISTS presences_univ CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print("✓ Base de données 'presences_univ' créée ou déjà existante")
        
        connection.commit()
        connection.close()
        return True
        
    except Exception as e:
        print(f"✗ Erreur lors de la création de la base de données: {e}")
        return False

def init_tables():
    """Initialise toutes les tables de la base de données"""
    try:
        app = create_app()
        with app.app_context():
            # Créer toutes les tables
            db.create_all()
            print("✓ Toutes les tables ont été créées avec succès")
            
            # Afficher les tables créées
            from app.models import User, Department, Track, AcademicYear, Subject, Course, Attendance
            tables = [
                'users', 'departments', 'tracks', 'academic_years', 
                'subjects', 'courses', 'sessions', 'attendances',
                'teacher_subjects', 'track_admins', 'department_admins'
            ]
            print(f"\nTables créées: {', '.join(tables)}")
            
        return True
        
    except Exception as e:
        print(f"✗ Erreur lors de la création des tables: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("INITIALISATION DE LA BASE DE DONNÉES")
    print("=" * 60)
    print()
    
    # Étape 1: Créer la base de données
    print("Étape 1: Création de la base de données...")
    if not create_database():
        print("\n✗ Échec de l'initialisation")
        exit(1)
    
    print()
    
    # Étape 2: Créer les tables
    print("Étape 2: Création des tables...")
    if not init_tables():
        print("\n✗ Échec de l'initialisation")
        exit(1)
    
    print()
    print("=" * 60)
    print("✓ INITIALISATION TERMINÉE AVEC SUCCÈS!")
    print("=" * 60)
    print()
    print("Compte administrateur par défaut:")
    print("  Email: admin@uir.ac.ma")
    print("  Mot de passe: admin123")
    print()
    print("Vous pouvez maintenant lancer l'application avec:")
    print("  python run.py")
    print()
