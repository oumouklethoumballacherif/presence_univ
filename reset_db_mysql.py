
import pymysql
from app import create_app
from app.models import db

# Configuration (Hardcoded for simplicity matching init_database.py)
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'MYSQL123',
    'database': 'presences_univ'
}

def reset_database():
    try:
        # Connect to MySQL engine (not specific DB yet)
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        
        with connection.cursor() as cursor:
            print("[INFO] Dropping database 'presences_univ'...")
            cursor.execute(f"DROP DATABASE IF EXISTS {DB_CONFIG['database']}")
            
            print("[INFO] Recreating database 'presences_univ'...")
            cursor.execute(f"CREATE DATABASE {DB_CONFIG['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
        connection.commit()
        connection.close()
        
        print("[SUCCESS] Database has been reset.")
        return True
    except Exception as e:
        print(f"[ERROR] Database reset failed: {e}")
        return False

def init_tables_and_data():
    try:
        app = create_app()
        with app.app_context():
            print("[INFO] Creating tables...")
            db.create_all()
            print("[SUCCESS] Tables created.")
            
            # Note: create_app() already creates the default admin user on startup if not exists.
            # But we can explicit it here if needed.
            return True
    except Exception as e:
        print(f"[ERROR] Table initialization failed: {e}")
        return False

if __name__ == '__main__':
    print("WARNING: This will delete all data in 'presences_univ'.")
    val = input("Type 'YES' to confirm: ")
    if val.strip() == 'YES':
        if reset_database():
            init_tables_and_data()
            print("\nDONE. Please restart your server manually: python run.py")
    else:
        print("Aborted.")
