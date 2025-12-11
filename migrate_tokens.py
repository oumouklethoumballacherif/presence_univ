"""Database migration script - create attendance_tokens table"""
import pymysql

# Connect directly to MySQL
connection = pymysql.connect(
    host='localhost',
    port=3306,
    user='root',
    password='MYSQL123',
    database='presences_univ'
)

try:
    with connection.cursor() as cursor:
        # Create attendance_tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_tokens (
                id INT AUTO_INCREMENT PRIMARY KEY,
                token VARCHAR(36) NOT NULL UNIQUE,
                course_id INT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        """)
        print("✓ Created attendance_tokens table")
    
    connection.commit()
    print("\n✓ Migration completed successfully!")
    
except Exception as e:
    print(f"\n! Migration failed: {e}")
    
finally:
    connection.close()
