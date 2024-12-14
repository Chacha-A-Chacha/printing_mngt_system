import os
from dotenv import load_dotenv
from app import create_app, db
from flask_migrate import Migrate

# Load environment variables from .env file
load_dotenv()

# Determine configuration based on environment
config_name = os.environ.get('FLASK_ENV', 'development')

# Create application instance
app = create_app(config_name)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

if __name__ == '__main__':
    # Retrieve configuration from environment or use defaults
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug_mode = config_name == 'development'

    # Ensure the app context is available for database operations
    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()

    # Run the application with flexible configuration
    app.run(
        host=host,
        port=port,
        debug=debug_mode
    )
