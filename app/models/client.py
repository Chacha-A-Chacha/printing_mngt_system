# models/client.py

from app import db
from . import BaseModel


class Client(BaseModel):
    __tablename__ = 'clients'

    name = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(50), nullable=False, unique=True, index=True)
    contact_info = db.Column(db.JSON, nullable=True)
    tax_id = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone_number': self.phone_number,
            'contact_info': self.contact_info,
            'tax_id': self.tax_id
        }

    def __repr__(self):
        return f"<Client {self.name} - {self.phone_number}>"
