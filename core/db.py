import sqlite3

_db_file = None

def init_db(db_file):
    global _db_file
    _db_file = db_file
    
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
                        (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS products 
                        (barcode TEXT PRIMARY KEY, 
                         name TEXT, 
                         price REAL, 
                         image_url TEXT, 
                         stock REAL DEFAULT 0, 
                         unit_type TEXT DEFAULT 'unit')''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS sales 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         date TEXT DEFAULT CURRENT_TIMESTAMP, 
                         total REAL, 
                         payment_method TEXT)''')
                          
        conn.execute('''CREATE TABLE IF NOT EXISTS sale_items 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         sale_id INTEGER, 
                         barcode TEXT, 
                         name TEXT, 
                         price REAL, 
                         quantity REAL, 
                         subtotal REAL,
                         FOREIGN KEY(sale_id) REFERENCES sales(id))''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS dicom 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         name TEXT UNIQUE, 
                         amount REAL DEFAULT 0, 
                         notes TEXT,
                         image_url TEXT,
                         last_updated TEXT DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS debtors 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         name TEXT UNIQUE, 
                         contact_info TEXT)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS debtor_tickets 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         debtor_id INTEGER NOT NULL,
                         date TEXT DEFAULT CURRENT_TIMESTAMP, 
                         total REAL NOT NULL,
                         amount_paid REAL DEFAULT 0,
                         status TEXT DEFAULT 'unpaid',
                         FOREIGN KEY(debtor_id) REFERENCES debtors(id) ON DELETE CASCADE)''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS debtor_ticket_items 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         ticket_id INTEGER NOT NULL,
                         barcode TEXT, 
                         name TEXT, 
                         price REAL, 
                         quantity REAL, 
                         subtotal REAL,
                         FOREIGN KEY(ticket_id) REFERENCES debtor_tickets(id) ON DELETE CASCADE)''')
        
        user = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
        if not user:
            from werkzeug.security import generate_password_hash
            hashed_pw = generate_password_hash('choripan1234')
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', hashed_pw))
        conn.commit()

def get_db_connection():
    if _db_file is None:
        raise RuntimeError("Database not initialized. Call init_db(db_file) first.")
    return sqlite3.connect(_db_file)