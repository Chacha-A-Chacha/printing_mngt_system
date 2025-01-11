import os
import logging
from flask import current_app
from datetime import timedelta


class BaseConfig:
    """
    Base configuration class using environment variables
    """

    # Application settings
    APP_NAME = os.environ.get('APP_NAME', 'Printing Management System')

    # Secret Key
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key-for-development')

    # Security settings
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() in ['true', 'on', '1']
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'true').lower() in ['true', 'on', '1']
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    REMEMBER_COOKIE_DURATION = timedelta(days=14)

    # Pagination and Stock Settings
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 20))
    LOW_STOCK_THRESHOLD = int(os.environ.get('LOW_STOCK_THRESHOLD', 10))

    # Logging Configuration
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'false').lower() in ['true', 'on', '1']
    LOGGING_LEVEL = os.environ.get('LOGGING_LEVEL', 'INFO').upper()

    # Login Settings
    LOGIN_DISABLED = os.environ.get('LOGIN_DISABLED', 'false').lower() in ['true', 'on', '1']
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    # LOGIN_LOCKOUT_DURATION = int(os.environ.get('LOGIN_LOCKOUT_DURATION', 15))

    # File Upload Settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', str(16 * 1024 * 1024)))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')

    @classmethod
    def init_app(cls, app):
        """
        Configure logging and other app-specific initialization.
        :param app: Flask application instance
        """
        # Logging Setup
        if cls.LOG_TO_STDOUT:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(cls.LOGGING_LEVEL)
            app.logger.addHandler(stream_handler)

        app.logger.setLevel(cls.LOGGING_LEVEL)
        app.logger.info(f"{cls.APP_NAME} initialized with {cls.__name__}")

        # Debugging details for loaded configuration
        app.logger.debug(f"Configuration Loaded: {cls.__name__}")
        app.logger.debug(f"SESSION_COOKIE_SECURE: {cls.SESSION_COOKIE_SECURE}")
        app.logger.debug(f"ITEMS_PER_PAGE: {cls.ITEMS_PER_PAGE}")
        app.logger.debug(f"LOGGING_LEVEL: {cls.LOGGING_LEVEL}")


class DatabaseConfig:
    """
    Database configuration with environment variable support
    """
    # SQLAlchemy Settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connection Pool Settings
    SQLALCHEMY_POOL_SIZE = int(os.environ.get('DATABASE_POOL_SIZE', 10))
    SQLALCHEMY_MAX_OVERFLOW = int(os.environ.get('DATABASE_MAX_OVERFLOW', 20))
    SQLALCHEMY_POOL_TIMEOUT = int(os.environ.get('DATABASE_POOL_TIMEOUT', 30))
    SQLALCHEMY_POOL_RECYCLE = int(os.environ.get('DATABASE_POOL_RECYCLE', 1800))  # 30 minutes

    # Query Performance Settings
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO', 'false').lower() in ['true', 'on', '1']
    SQLALCHEMY_RECORD_QUERIES = os.environ.get('SQLALCHEMY_RECORD_QUERIES', 'false').lower() in ['true', 'on', '1']
    DATABASE_QUERY_TIMEOUT = int(os.environ.get('DATABASE_QUERY_TIMEOUT', 0.5))  # In seconds

    @staticmethod
    def get_database_uri(config_name):
        """
        Generate database URI based on configuration environment

        Args:
            config_name: Name of the configuration environment
        Returns:
            str: Database connection URI
        """
        # For testing, always use in-memory SQLite
        if config_name == 'testing':
            return 'sqlite:///:memory:'

        # Database connection parameters from environment
        db_user = os.environ.get('DATABASE_USER')
        db_password = os.environ.get('DATABASE_PASSWORD')
        db_host = os.environ.get('DATABASE_HOST', 'localhost')
        db_port = os.environ.get('DATABASE_PORT', '3306')  # Default MySQL port
        db_name = os.environ.get('DATABASE_NAME', 'printing_management_db')

        # Use environment variable for complete database URL if provided
        db_url = os.environ.get('DATABASE_URL')

        if db_url:
            return db_url

        # Construct URL if individual parameters are provided
        if all([db_user, db_password, db_host, db_name]):
            return f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

        # Fallback to SQLite
        default_db_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            '..',
            'printing_management.db'
        )
        return f'sqlite:////{default_db_path}'

    @staticmethod
    def init_db(app):
        """
        Initialize database-specific settings

        Args:
            app: Flask application instance
        """
        app.logger.debug("Initializing database settings...")

        # Log database connection details (excluding sensitive info)
        db_host = os.environ.get('DATABASE_HOST', 'localhost')
        db_name = os.environ.get('DATABASE_NAME', 'printing_management_db')
        app.logger.info(f"Connecting to database: {db_name} on {db_host}")

        # Log pool settings
        app.logger.debug(f"Pool Size: {DatabaseConfig.SQLALCHEMY_POOL_SIZE}")
        app.logger.debug(f"Max Overflow: {DatabaseConfig.SQLALCHEMY_MAX_OVERFLOW}")
        app.logger.debug(f"Pool Recycle: {DatabaseConfig.SQLALCHEMY_POOL_RECYCLE}")


class DevelopmentConfig(BaseConfig, DatabaseConfig):
    """
    Development-specific configuration
    """
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = DatabaseConfig.get_database_uri('development')


class ProductionConfig(BaseConfig, DatabaseConfig):
    """
    Production-specific configuration
    """
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = DatabaseConfig.get_database_uri('production')


class TestingConfig(BaseConfig, DatabaseConfig):
    """
    Testing-specific configuration
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = DatabaseConfig.get_database_uri('testing')


def get_config(config_name):
    """
    Factory function to return the appropriate configuration class

    :param config_name: Name of the configuration ('development', 'production', 'testing')
    :return: Configuration class
    """
    config_mapping = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }

    return config_mapping.get(config_name.lower(), DevelopmentConfig)
