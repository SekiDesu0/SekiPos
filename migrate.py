import sqlite3

DB_FILE = 'db/pos_database.db'

def upgrade_db():
    try:
        with sqlite3.connect(DB_FILE) as conn:

            conn.execute("ALTER TABLE dicom ADD COLUMN image_url TEXT;")
            print("Successfully added 'image_url' column.")

            conn.commit()
            print("Migration complete. Your data is intact.")
            
    except sqlite3.OperationalError as e:
        print(f"Skipped: {e}. (This usually means the columns already exist, so you're fine).")

if __name__ == '__main__':
    upgrade_db()