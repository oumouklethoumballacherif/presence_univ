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
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN current_year_id INT")
            cursor.execute("ALTER TABLE users ADD CONSTRAINT fk_users_current_year FOREIGN KEY (current_year_id) REFERENCES academic_years(id)")
            print("✓ Added current_year_id column to users table")
        except pymysql.err.OperationalError as e:
            if '1060' in str(e):  # Column already exists
                print("- current_year_id column already exists")
            else:
                print(f"! Error: {e}")
    
    connection.commit()
    print("\n✓ Migration completed successfully!")
    
finally:
    connection.close()
