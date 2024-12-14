from app import db
from . import BaseModel


class Supplier(BaseModel):
    name = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.JSON, nullable=True)

    def __repr__(self):
        return f"<Supplier {self.name}>"
