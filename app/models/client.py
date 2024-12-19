# models/client.py

from app import db
from . import BaseModel


class Client(BaseModel):
    name = db.Column(db.String(100), nullable=True)  # TODO: enter the phone_number to retrieve client data for job commit
    contact_info = db.Column(db.JSON, nullable=True)
    tax_id = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"<Client {self.name}>"