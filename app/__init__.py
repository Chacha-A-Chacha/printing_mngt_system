from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from .config import Config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app(config_class=Config):
    """
    Application factory function to create and configure the Flask application

    Args:
        config_class (object): Configuration class for the application

    Returns:
        Flask: Configured Flask application instance
    """
    # Create Flask app instance
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register blueprints
    from .routes import (
        auth_bp,
        in_house_printing_bp,
        outsourced_production_bp,
        client_bp,
        supplier_bp,
        reporting_bp
    )

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(in_house_printing_bp, url_prefix='/in-house')
    app.register_blueprint(outsourced_production_bp, url_prefix='/production')
    app.register_blueprint(client_bp, url_prefix='/clients')
    app.register_blueprint(supplier_bp, url_prefix='/suppliers')
    app.register_blueprint(reporting_bp, url_prefix='/reports')

    return app