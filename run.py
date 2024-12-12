import os
from app import create_app, db
from flask_migrate import Migrate

# Create application instance
app = create_app()

# Initialize Flask-Migrate
migrate = Migrate(app, db)

if __name__ == '__main__':
    # Ensure the app context is available for database operations
    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()

    # Run the application
    # Use different configurations based on environment
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=debug_mode
    )
