# create_database.py
import sqlite3

DB_NAME = 'progress.db'

print(f"Setting up database '{DB_NAME}'...")

# Connect to the database (this will create the file if it doesn't exist)
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Create the main table to track our progress
# status can be: 'pending', 'in_progress', 'completed', 'failed'
cursor.execute('''
CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    last_updated TEXT NOT NULL
)
''')

# Save the changes and close the connection
conn.commit()
conn.close()

print("Database setup complete.")