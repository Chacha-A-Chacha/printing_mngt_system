import os
from datetime import timedelta


class Config:
    """
    Base configuration class for the application
    """
    # Secret key for sessions and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-hard-to-guess-secret-key'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:////' + os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'printing_management.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Application settings
    APP_NAME = 'Printing Management System'

    # Security settings
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_DURATION = timedelta(days=14)

    # Logging configuration
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'false').lower() in ['true', 'on', '1']

    # Pagination settings
    ITEMS_PER_PAGE = 20

    # Notification settings
    LOW_STOCK_THRESHOLD = 10  # Percentage of minimum stock level


class DevelopmentConfig(Config):
    """
    Development-specific configuration
    """
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """
    Production-specific configuration
    """
    DEBUG = False


class TestingConfig(Config):
    """
    Testing-specific configuration
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

