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
    custom_attributes = db.Column(db.JSON, nullable=True)

    def __repr__(self):
        return f"<Material {self.name}>"


class Job(BaseModel):
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship('Client', backref=db.backref('jobs', lazy=True))
    description = db.Column(db.String(255), nullable=True)
    total_profit = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f"<Job {self.id} for Client {self.client.name}>"


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
