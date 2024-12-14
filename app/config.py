import os
from datetime import timedelta


class BaseConfig:
    """
    Base configuration class for the application
    """
    # Application settings
    APP_NAME = 'Printing Management System'

    # Security settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-hard-to-guess-secret-key'
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_DURATION = timedelta(days=14)

    # Logging configuration
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'false').lower() in ['true', 'on', '1']

    # Pagination settings
    ITEMS_PER_PAGE = 20

    # Notification settings
    LOW_STOCK_THRESHOLD = 10  # Percentage of minimum stock level


class DatabaseConfig:
    """
    Database configuration base class
    """
    # Database configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def get_database_uri(config_name):
        """
        Generate database URI based on configuration environment
        """
        if config_name == 'testing':
            return 'sqlite:///:memory:'

        default_db_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            '..',
            'printing_management.db'
        )
        return os.environ.get('DATABASE_URL') or f'sqlite:////{default_db_path}'


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
