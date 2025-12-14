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
        try:
            cursor.execute("ALTER TABLE tracks ADD COLUMN code VARCHAR(20)")
            # cursor.execute("UPDATE tracks SET code = CONCAT('TR', id) WHERE code IS NULL") # Optional: Populate existing
            print("✓ Added code column to tracks table")
        except pymysql.err.OperationalError as e:
            if '1060' in str(e):  # Column already exists
                print("- current_year_id column already exists")
            else:
                print(f"! Error: {e}")
    
    connection.commit()
    print("\n✓ Migration completed successfully!")
    
finally:
    connection.close()
