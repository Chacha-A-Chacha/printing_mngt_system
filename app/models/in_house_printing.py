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


class MachineReading(BaseModel):
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    start_meter = db.Column(db.Integer, nullable=False)
    end_meter = db.Column(db.Integer, nullable=False)
    material_usage = db.Column(db.Float, nullable=False)

    def calculate_total_usage(self):
        return self.end_meter - self.start_meter
