import sys
import os
from werkzeug.security import generate_password_hash
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Ensure this path is correct and points to your app's directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your Flask app and db instance
from app import app, db, User

def add_user(username, email, password, is_admin=False):
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            print(f"Error: User with username '{username}' or email '{email}' already exists.")
            return

        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password, is_admin=is_admin)
        
        db.session.add(new_user)
        try:
            db.session.commit()
            print(f"User '{username}' added successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding user: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python add_user_to_db.py <username> <email> <password> [is_admin]")
        sys.exit(1)

    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    is_admin = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else False

    add_user(username, email, password, is_admin)