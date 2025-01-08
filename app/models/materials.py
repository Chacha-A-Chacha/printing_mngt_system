from datetime import datetime

from . import BaseModel
from .. import db


class Material(BaseModel):
    __tablename__ = 'materials'

    material_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Primary category
    type = db.Column(db.String(50), nullable=False)  # Subcategory/type
    unit_of_measure = db.Column(db.String(20), nullable=False)

    # Stock Management
    stock_level = db.Column(db.Float, default=0.0)
    min_threshold = db.Column(db.Float, nullable=False)
    reorder_quantity = db.Column(db.Float, nullable=False)

    # Cost Management
    cost_per_unit = db.Column(db.Float, nullable=False)

    # Specifications
    specifications = db.Column(db.JSON, nullable=True)  # For dimensions, weight, etc.

    # Supplier Relationship
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    supplier = db.relationship('Supplier', backref=db.backref('materials', lazy=True))

    def serialize(self):
        return {
            "id": self.id,
            "material_code": self.material_code,
            "name": self.name,
            "category": self.category,
            "type": self.type,
            "unit_of_measure": self.unit_of_measure,
            "stock_level": self.stock_level,
            "min_threshold": self.min_threshold,
            "reorder_quantity": self.reorder_quantity,
            "cost_per_unit": self.cost_per_unit,
            "specifications": self.specifications,
            "supplier_id": self.supplier_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class MaterialUsage(BaseModel):
    __tablename__ = 'material_usages'

    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    quantity_used = db.Column(db.Float, nullable=False)
    unit_of_measure = db.Column(db.String(20), nullable=False)
    usage_date = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    wastage = db.Column(db.Float, default=0.0)
    notes = db.Column(db.String(255))

    # Relationships
    material = db.relationship('Material', backref='usages')
    job = db.relationship('Job', backref='material_usages')
    # user = db.relationship('User', backref='material_usages')


