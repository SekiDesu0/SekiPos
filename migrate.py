import sqlite3

DB_FILE = 'db/pos_database.db'

def upgrade_db():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            # Add stock column
            # conn.execute("ALTER TABLE products ADD COLUMN stock REAL DEFAULT 0")
            # print("Successfully added 'stock' column.")
            
            # # App.py also expects unit_type, adding it to prevent future headaches
            # conn.execute("ALTER TABLE products ADD COLUMN unit_type TEXT DEFAULT 'unit'")
            # print("Successfully added 'unit_type' column.")

            conn.execute("ALTER TABLE dicom ADD COLUMN image_url TEXT;")
            print("Successfully added 'image_url' column.")

            conn.commit()
            print("Migration complete. Your data is intact.")
            
    except sqlite3.OperationalError as e:
        print(f"Skipped: {e}. (This usually means the columns already exist, so you're fine).")

if __name__ == '__main__':
    upgrade_db()