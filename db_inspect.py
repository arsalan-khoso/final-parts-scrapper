import sqlite3
import os

# Path to your database file
db_path = 'instance/users.db'

def inspect_user_table():
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n--- Contents of 'user' table ---")
    
    # Get column names
    cursor.execute("PRAGMA table_info(user);")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    print("Columns:", ", ".join(column_names))
    
    # Get all rows
    cursor.execute("SELECT * FROM user;")
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            print(row)
    else:
        print("(Table is empty)")

    conn.close()

if __name__ == "__main__":
    inspect_user_table()
    print("\nUser table inspection complete.")