from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
import structlog


# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
logger = structlog.get_logger()


def create_app(config_name):
    """
    Application factory function to create and configure the Flask application

    Args:
        config_name (str, optional): Name of the configuration environment.
                                     Defaults to 'development'.

    Returns:
        Flask: Configured Flask application instance
    """
    # Import config dynamically to avoid circular imports
    from .config import get_config

    # Create Flask app instance
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

    # Select and load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Configure logging if needed
    if app.config.get('LOG_TO_STDOUT'):
        import logging
        import sys
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Configure login manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Optional: Set login message
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Register blueprints
    _register_blueprints(app)

    # Optional: Add any additional app setup
    _setup_error_handlers(app)

    return app


def _register_blueprints(app):
    """
    Register application blueprints

    Args:
        app (Flask): Flask application instance
    """
    from .routes import (
        auth_bp,
        in_house_printing_bp,
        outsourced_production_bp,
        client_bp,
        jobs_bp,
        materials_bp,
        supplier_bp,
        reporting_bp
    )

    blueprints = [
        (auth_bp, '/auth'),
        (in_house_printing_bp, '/in-house'),
        (outsourced_production_bp, '/production'),
        (client_bp, '/clients'),
        (jobs_bp, '/print'),
        (materials_bp, '/materials'),
        (supplier_bp, '/suppliers'),
        (reporting_bp, '/reports')
    ]

    for blueprint, url_prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=url_prefix)


def _setup_error_handlers(app):
    """
    Set up custom error handlers for the application

    Args:
        app (Flask): Flask application instance
    """

    @app.errorhandler(404)
    def page_not_found(error):
        """
        Custom 404 error handler

        Args:
            error: Error object

        Returns:
            Rendered error page or response
        """
        app.logger.error(f'Page not found: {error}')
        return 'Page not found', 404

    @app.errorhandler(500)
    def internal_server_error(error):
        """
        Custom 500 error handler

        Args:
            error: Error object

        Returns:
            Rendered error page or response
        """
        app.logger.error(f'Server Error: {error}')
        db.session.rollback()  # Rollback any pending database changes
        return 'An unexpected error occurred', 500
