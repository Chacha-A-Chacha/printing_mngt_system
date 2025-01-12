from datetime import datetime

from . import BaseModel
from .. import db

from .user import User
from .supplier import Supplier


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
    custom_attributes = db.Column(db.JSON, nullable=True)

    # Supplier Relationship
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    supplier = db.relationship('Supplier', backref=db.backref('materials', lazy=True))

    def serialize(self):
        base_data = {
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
            "custom_attributes": self.custom_attributes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

        # Add relationships if loaded
        if self.supplier:
            base_data["supplier"] = {
                "id": self.supplier.id,
                "name": self.supplier.name
            }

        return base_data


class MaterialUsage(BaseModel):
    __tablename__ = 'material_usages'

    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    quantity_used = db.Column(db.Float, nullable=False)
    unit_of_measure = db.Column(db.String(20), nullable=False)
    usage_date = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    wastage = db.Column(db.Float, default=0.0)
    cost = db.Column(db.Float, nullable=False)  # Added from JobMaterialUsage
    notes = db.Column(db.String(255))

    # Relationships
    material = db.relationship('Material', backref='usages')
    job = db.relationship('Job', foreign_keys=[job_id])
    user = db.relationship('User', backref='material_usages')

    def serialize(self):
        return {
            "id": self.id,
            "material_id": self.material_id,
            "job_id": self.job_id,
            "quantity_used": self.quantity_used,
            "unit_of_measure": self.unit_of_measure,
            "wastage": self.wastage,
            "cost": self.cost,
            "notes": self.notes,
            "user_id": self.user_id,
            "usage_date": self.usage_date.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class StockTransaction(BaseModel):
    __tablename__ = 'stock_transactions'

    TRANSACTION_TYPES = ['RESTOCK', 'ADJUSTMENT', 'RETURN']

    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    previous_stock = db.Column(db.Float, nullable=False)
    new_stock = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    reference_number = db.Column(db.String(50))
    notes = db.Column(db.String(255))
    cost_per_unit = db.Column(db.Float, nullable=True)  # Track cost at time of transaction

    # Relationships
    material = db.relationship('Material', backref='stock_transactions')
    user = db.relationship('User', backref='stock_transactions')
    supplier = db.relationship('Supplier', backref='stock_transactions')

    def serialize(self):
        return {
            "id": self.id,
            "material_id": self.material_id,
            "transaction_type": self.transaction_type,
            "quantity": self.quantity,
            "previous_stock": self.previous_stock,
            "new_stock": self.new_stock,
            "reference_number": self.reference_number,
            "cost_per_unit": self.cost_per_unit,
            "supplier": self.supplier.serialize() if self.supplier else None,
            "notes": self.notes,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
