import os
import sqlite3
import sys

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db')
DB_FILE = os.path.join(DB_DIR, 'pos_database.db')


def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    return sqlite3.connect(DB_FILE)


def table_exists(conn, table_name):
    result = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return result is not None


def column_exists(conn, table_name, column_name):
    result = conn.execute(f"PRAGMA table_info({table_name})").fetchone()
    if not result:
        return False
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(col[1] == column_name for col in columns)


def migrate():
    conn = get_connection()
    migrations_applied = []

    if not table_exists(conn, 'users'):
        conn.execute('''CREATE TABLE users 
                        (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
        migrations_applied.append("Created table: users")

    if not table_exists(conn, 'products'):
        conn.execute('''CREATE TABLE products 
                        (barcode TEXT PRIMARY KEY, 
                         name TEXT, 
                         price REAL, 
                         image_url TEXT, 
                         stock REAL DEFAULT 0, 
                         unit_type TEXT DEFAULT 'unit')''')
        migrations_applied.append("Created table: products")

    if not table_exists(conn, 'sales'):
        conn.execute("""CREATE TABLE sales 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         date TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')), 
                         total REAL, 
                         payment_method TEXT)""")
        migrations_applied.append("Created table: sales")

    if not table_exists(conn, 'sale_items'):
        conn.execute('''CREATE TABLE sale_items 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         sale_id INTEGER, 
                         barcode TEXT, 
                         name TEXT, 
                         price REAL, 
                         quantity REAL, 
                         subtotal REAL,
                         FOREIGN KEY(sale_id) REFERENCES sales(id))''')
        migrations_applied.append("Created table: sale_items")

    if not table_exists(conn, 'debtors'):
        conn.execute('''CREATE TABLE debtors 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         name TEXT UNIQUE, 
                         contact_info TEXT)''')
        migrations_applied.append("Created table: debtors")

    if not table_exists(conn, 'debtor_tickets'):
        conn.execute("""CREATE TABLE debtor_tickets 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         debtor_id INTEGER NOT NULL,
                         date TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')), 
                         total REAL NOT NULL,
                         amount_paid REAL DEFAULT 0,
                         status TEXT DEFAULT 'unpaid',
                         FOREIGN KEY(debtor_id) REFERENCES debtors(id) ON DELETE CASCADE)""")
        migrations_applied.append("Created table: debtor_tickets")

    if not table_exists(conn, 'debtor_ticket_items'):
        conn.execute('''CREATE TABLE debtor_ticket_items 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         ticket_id INTEGER NOT NULL,
                         barcode TEXT, 
                         name TEXT, 
                         price REAL, 
                         quantity REAL, 
                         subtotal REAL,
                         FOREIGN KEY(ticket_id) REFERENCES debtor_tickets(id) ON DELETE CASCADE)''')
        migrations_applied.append("Created table: debtor_ticket_items")

    if not table_exists(conn, 'idempotency_keys'):
        conn.execute('''CREATE TABLE idempotency_keys 
                        (key TEXT PRIMARY KEY, 
                         endpoint TEXT NOT NULL,
                         created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')))''')
        migrations_applied.append("Created table: idempotency_keys")

    if not table_exists(conn, 'expenses'):
        conn.execute("""CREATE TABLE expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TIMESTAMP DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
            description TEXT NOT NULL,
            amount INTEGER NOT NULL
        )""")
        migrations_applied.append("Created table: expenses")

    if table_exists(conn, 'users'):
        user = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
        if not user:
            from werkzeug.security import generate_password_hash
            hashed_pw = generate_password_hash('choripan1234')
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', hashed_pw))
            migrations_applied.append("Created default admin user")

    if table_exists(conn, 'expenses'):
        try:
            conn.execute("UPDATE expenses SET date = date || ' 00:00:00' WHERE length(date) = 10 AND date NOT LIKE '% %'")
            migrations_applied.append("Normalized expenses date format")
        except Exception:
            pass

    conn.commit()
    conn.close()

    if migrations_applied:
        print("Migrations applied:")
        for m in migrations_applied:
            print(f"  - {m}")
    else:
        print("No migrations needed. Database is up to date.")


if __name__ == '__main__':
    migrate()
