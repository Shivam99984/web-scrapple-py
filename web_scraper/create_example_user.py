from app import app, db, User, ScheduledJob, ScrapingResult
from datetime import datetime

def create_example_user():
    with app.app_context():
        try:
            # Delete all existing data
            ScrapingResult.query.delete()
            ScheduledJob.query.delete()
            User.query.delete()
            
            # Create example user
            example_user = User(
                username='admin',
                email='admin@example.com',
                created_at=datetime.utcnow()
            )
            example_user.set_password('admin123')  # Set a secure password
            
            # Add to database
            db.session.add(example_user)
            db.session.commit()
            
            print("All data cleared and example user created successfully!")
            print("Username: admin")
            print("Password: admin123")
            print("Email: admin@example.com")
            
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred: {str(e)}")

if __name__ == '__main__':
    create_example_user() 