from app import create_app
from models import db, Admin
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
import os

###Only needs to be run once to create the users ###

def create_admins():
    # Load environment variables
    load_dotenv()
    
    # Create the Flask app context
    app = create_app()
    with app.app_context():
        # Get the pepper from the environment
        pepper = os.environ.get('PASSWORD_PEPPER', 'default-pepper-change-in-production')
        
        # Define admin credentials
        admins = [
            {"username": "Omer", "password": "Omer1234"},
            {"username": "Raul", "password": "Raul1234"}
        ]
        
        for admin_data in admins:
            # Check if the admin already exists
            existing_admin = Admin.query.filter_by(username=admin_data["username"]).first()
            if existing_admin:
                print(f"Admin '{admin_data['username']}' already exists.")
            else:
                # Create a new admin
                new_admin = Admin(username=admin_data["username"])
                peppered_password = admin_data["password"] + pepper
                new_admin.password_hash = generate_password_hash(peppered_password)
                db.session.add(new_admin)
                print(f"Admin '{admin_data['username']}' created successfully!")
        
        # Commit the changes to the database
        db.session.commit()
        print("All admins created/verified!")

if __name__ == "__main__":
    create_admins()