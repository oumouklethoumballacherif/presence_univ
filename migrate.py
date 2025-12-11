"""Database migration script - add level column to tracks"""
import pymysql

# Connect directly to MySQL
connection = pymysql.connect(
    host='localhost',
    port=3306,
    user='root',
    password='',
    database='presences_univ'
)

try:
    with connection.cursor() as cursor:
        # Add level column to tracks table
        try:
            cursor.execute("ALTER TABLE tracks ADD COLUMN level VARCHAR(20) NOT NULL DEFAULT 'licence'")
            print("✓ Added level column to tracks table")
        except pymysql.err.OperationalError as e:
            if '1060' in str(e):  # Column already exists
                print("- level column already exists in tracks")
            else:
                print(f"! tracks level error: {e}")
    
    connection.commit()
    print("\n✓ Migration completed successfully!")
    
finally:
    connection.close()
