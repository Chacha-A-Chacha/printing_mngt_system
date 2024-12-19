
from . import BaseModel
from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from .. import db


class MachineReading(BaseModel):
    __tablename__ = 'machine_readings'

    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    job = relationship('Job', backref=db.backref('machine_readings', lazy=True))

    start_meter = Column(Float, nullable=False)
    end_meter = Column(Float, nullable=False)

    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    material = relationship('Material', backref=db.backref('machine_readings', lazy=True))

    material_usage = Column(Float, nullable=False)

    def calculate_total_usage(self):
        return self.end_meter - self.start_meter

    def __repr__(self):
        return f"<MachineReading Job {self.job_id} Material {self.material.name}>"
