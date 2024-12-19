from . import BaseModel
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, func


class MachineReading(BaseModel):
    __tablename__ = 'machine_readings'

    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    start_meter = Column(Float, nullable=False)
    end_meter = Column(Float, nullable=False)
    material_usage = Column(Float, nullable=False)
