import sqlite3

def create_tables():
    conn = sqlite3.connect('career_counselor.db')
    cursor = conn.cursor()

    # 1. users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            email TEXT,
            password TEXT
        )
    ''')

    # 2. recruiter table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recruiter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            email TEXT,
            password TEXT
        )
    ''')

    # 3. owner table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS owner (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    ''')

    # 4. job table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recruiter_id INTEGER,
            company TEXT NOT NULL,
            designation TEXT NOT NULL,
            experience_required TEXT,
            qualification TEXT,
            skills_required TEXT,
            contact_number TEXT,
            email TEXT,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 5. apply table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apply (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant_name TEXT,
            applicant_email TEXT,
            qualification TEXT,
            university TEXT,
            experience INTEGER,
            skills TEXT,
            resume_path TEXT,
            recruiter_id INTEGER,
            job_id INTEGER,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 6. feedback table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            experience TEXT,
            user_type TEXT,
            suggestions TEXT,
            rating INTEGER
        )
    ''')

    conn.commit()
    conn.close()
    print("All tables created successfully.")

if __name__ == '__main__':
    create_tables()
