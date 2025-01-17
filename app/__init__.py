from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
import structlog
from sqlalchemy import event
from sqlalchemy.engine import Engine
import ssl
from retry import retry
import time

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
logger = structlog.get_logger()


# Database connection retry decorator
@retry(tries=3, delay=2, backoff=2)
def init_db_with_retry(app):
    """Initialize database with retry logic"""
    try:
        db.init_app(app)
        # Test connection
        with app.app_context():
            db.engine.connect()
        logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise


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

    # Load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Enhanced CORS configuration
    cors_options = {
        'origins': app.config['CORS_ORIGINS'],
        'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
        'allow_headers': ['Content-Type', 'Authorization', 'Cache-Control', 'Pragma', 'If-Match', 'If-None-Match',
                          'Expires'],
        'expose_headers': ['Content-Range', 'X-Total-Count'],
        'supports_credentials': True
    }
    CORS(app, **cors_options)
    logger.debug(f"CORS Origins configured: {app.config['CORS_ORIGINS']}")

    # Configure logging
    if app.config.get('LOG_TO_STDOUT'):
        _setup_logging(app)

    # Database specific configurations
    _configure_database(app)

    # Initialize extensions with retry
    init_db_with_retry(app)
    migrate.init_app(app, db, directory=app.config.get('MIGRATIONS_DIR', 'migrations'))

    # Enhanced security configurations
    _configure_security(app)

    # Configure login manager with enhanced security
    _configure_login_manager(app)

    with app.app_context():
        _init_database_models(app)

    # Register blueprints and error handlers
    _register_blueprints(app)
    _setup_error_handlers(app)

    # Log startup information
    app.logger.info(f"Starting application in {config_name} mode")
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
        machine_logs_bp,
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
        (machine_logs_bp, '/machine'),
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


def _configure_database(app):
    """Configure database specific settings"""
    # MySQL specific configurations
    if 'mysql' in app.config['SQLALCHEMY_DATABASE_URI']:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': app.config.get('SQLALCHEMY_POOL_SIZE', 10),
            'pool_recycle': app.config.get('SQLALCHEMY_POOL_RECYCLE', 3600),
            'pool_pre_ping': True,
            'connect_args': {
                'ssl': {
                    'ssl_ca': app.config.get('MYSQL_SSL_CA'),
                } if app.config.get('MYSQL_SSL_CA') else None,
            }
        }

    # PostgreSQL specific configurations
    elif 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': app.config.get('SQLALCHEMY_POOL_SIZE', 10),
            'pool_pre_ping': True,
            'connect_args': {
                'sslmode': 'verify-full',
                'sslcert': app.config.get('POSTGRES_SSL_CERT'),
                'sslkey': app.config.get('POSTGRES_SSL_KEY'),
                'sslrootcert': app.config.get('POSTGRES_SSL_ROOTCERT'),
            } if app.config.get('POSTGRES_SSL_CERT') else {}
        }

    # Configure SQLAlchemy performance monitoring
    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault('query_start_time', []).append(time.time())

    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = time.time() - conn.info['query_start_time'].pop()
        if total > app.config.get('SLOW_QUERY_THRESHOLD', 0.5):
            logger.warning(f"Slow query detected: {total:.2f}s\n{statement}")


def _configure_security(app):
    """Configure enhanced security settings"""

    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Content-Security-Policy'] = app.config.get(
            'CONTENT_SECURITY_POLICY',
            "default-src 'self'; script-src 'self'; style-src 'self'"
        )
        return response

    # Session configuration
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = app.config.get('PERMANENT_SESSION_LIFETIME', 3600)


def _init_database_models(app):
    """Initialize database models and perform initial setup"""
    # Import models
    from .models.user import User, Role, init_roles
    from .models.supplier import Supplier
    from .models.client import Client
    from .models.materials import Material, MaterialUsage, StockTransaction
    from .models.job import Job, JobNote, JobTimeframeChangeLog
    from .models.expenses import JobExpense

    # Create all tables
    db.create_all()

    # Only then initialize roles
    from .models.user import init_roles
    try:
        init_roles(app)
    except Exception as e:
        app.logger.warning(f"Role initialization skipped: {str(e)}")


def _setup_logging(app):
    """Setup enhanced logging configuration"""
    import logging
    import sys

    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)

    app.logger.addHandler(stream_handler)
    app.logger.setLevel(app.config.get('LOG_LEVEL', logging.INFO))


def _configure_login_manager(app):
    """Configure Flask-Login with enhanced security settings"""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Enhanced security settings
    login_manager.session_protection = "strong"  # Enable strong session protection
    login_manager.refresh_view = 'auth.login'  # View to refresh session
    login_manager.needs_refresh_message = 'Please re-authenticate to protect your session.'
    login_manager.needs_refresh_message_category = 'info'

    # Configure session lifetime
    app.config['REMEMBER_COOKIE_DURATION'] = app.config.get('REMEMBER_COOKIE_DURATION', 3600)  # 1 hour
    app.config['REMEMBER_COOKIE_SECURE'] = True
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'

    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        from .models.user import User
        try:
            user = User.query.get(int(user_id))
            if user and user.is_active:
                # Update last activity timestamp
                user.update_last_login()
                return user
            return None
        except Exception as e:
            app.logger.error(f"Error loading user {user_id}: {str(e)}")
            return None

    # Unauthorized callback
    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import jsonify
        return jsonify({
            "error": "Unauthorized",
            "message": "You must be logged in to access this resource"
        }), 401

    # Handle session protection failures
    @app.errorhandler(401)
    def handle_unauthorized(error):
        from flask import jsonify
        app.logger.warning(f"Unauthorized access attempt: {error}")
        return jsonify({
            "error": "Unauthorized",
            "message": "Authentication failed or session expired"
        }), 401

    app.logger.info("Login manager configured with enhanced security settings")