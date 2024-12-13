# models/in_house_printing.py

from app import db
from . import BaseModel
from .client import Client


class Material(BaseModel):
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    stock_level = db.Column(db.Float, nullable=False)
    min_threshold = db.Column(db.Float, nullable=False)
    cost_per_sq_meter = db.Column(db.Float, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    custom_attributes = db.Column(db.JSON, nullable=True)

    def serialize(self):
        """
        Serialize material attributes into a dictionary for API responses.
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.mt_type,
            "stock_level": self.stock_level,
            "min_threshold": self.min_threshold,
            "cost_per_sq_meter": self.cost_per_sq_meter,
            "supplier_id": self.supplier_id,
            "custom_attributes": self.custom_attributes
        }

    def __repr__(self):
        return f"<Material {self.name}>"


class Job(BaseModel):
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship('Client', backref=db.backref('jobs', lazy=True))
    description = db.Column(db.String(255), nullable=True)
    total_profit = db.Column(db.Float, nullable=True)
    payment_status = db.Column(db.Enum('Paid', 'Partially Paid', 'Unpaid', name='payment_status'), nullable=False,
                               default='Unpaid')
    total_amount = db.Column(db.Float, nullable=False)
    amount_paid = db.Column(db.Float, nullable=False, default=0)

    def calculate_outstanding_amount(self):
        return self.total_amount - self.amount_paid

    def update_payment(self, payment_amount):
        self.amount_paid += payment_amount
        if self.amount_paid >= self.total_amount:
            self.payment_status = 'Paid'
        elif self.amount_paid > 0:
            self.payment_status = 'Partially Paid'
        else:
            self.payment_status = 'Unpaid'


class MachineReading(BaseModel):
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    job = db.relationship('Job', backref=db.backref('machine_readings', lazy=True))
    start_meter = db.Column(db.Integer, nullable=False)
    end_meter = db.Column(db.Integer, nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    material = db.relationship('Material', backref=db.backref('machine_readings', lazy=True))
    material_usage = db.Column(db.Float, nullable=False)

    def calculate_total_usage(self):
        return self.end_meter - self.start_meter

    def __repr__(self):
        return f"<MachineReading Job {self.job_id} Material {self.material.name}>"
