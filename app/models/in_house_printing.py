# models/in_house_printing.py

from app import db
from . import BaseModel


class Material(BaseModel):
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    stock_level = db.Column(db.Float, nullable=False)
    min_threshold = db.Column(db.Float, nullable=False)
    cost_per_sq_meter = db.Column(db.Float, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    supplier = db.relationship('Supplier', backref=db.backref('materials', lazy=True))
    custom_attributes = db.Column(db.JSON, nullable=True)

    def serialize(self):
        """
        Serialize material attributes into a dictionary for API responses.
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "stock_level": self.stock_level,
            "min_threshold": self.min_threshold,
            "cost_per_sq_meter": self.cost_per_sq_meter,
            "supplier_id": self.supplier_id,
            "custom_attributes": self.custom_attributes
        }

    def __repr__(self):
        return f"<Material {self.name}>"
