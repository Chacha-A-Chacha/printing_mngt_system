# models/__init__.py

from .. import db
from datetime import datetime


class BaseModel(db.Model):
    """
    Base model with common fields for all models
    """
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def save(self):
        """
        Save the current model instance to the database.
        If an exception occurs, rollback the session to maintain session consistency.
        """
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Optionally, re-raise the exception or handle it as needed.
            # For example, you could log the error or return a custom error response.
            raise e

    def delete(self):
        """
        Delete the current model instance from the database
        """
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def get_by_id(cls, id):
        """
        Retrieve a model instance by its ID

        Args:
            id (int): Primary key of the model instance

        Returns:
            Model instance or None
        """
        return cls.query.get(id)
