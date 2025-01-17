
from . import BaseModel
from sqlalchemy import Column, Integer, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from .. import db


class Machine(BaseModel):
    __tablename__ = 'machines'

    name = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    serial_number = Column(String(100), unique=True, nullable=False)
    status = Column(String(50), default='active')  # active, maintenance, inactive

    readings = relationship('MachineReading', back_populates='machine')

    def get_latest_reading(self):
        return self.readings.order_by(MachineReading.created_at.desc()).first()


class MachineReading(BaseModel):
    __tablename__ = 'machine_readings'

    # Machine relationship
    machine_id = Column(Integer, ForeignKey('machines.id'), nullable=False)
    machine = relationship('Machine', back_populates='readings')

    # Job relationship (this will give us access to material usage data)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    job = relationship('Job', backref=db.backref('machine_readings', lazy=True))

    # Meter readings
    start_meter = Column(Float, nullable=False)
    end_meter = Column(Float, nullable=False)

    # Optional operator tracking
    operator_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    operator = relationship('User', backref=db.backref('machine_readings', lazy=True))

    def calculate_meter_difference(self):
        """Calculate the difference between end and start meter readings"""
        return self.end_meter - self.start_meter

    def __repr__(self):
        return f"<MachineReading Machine {self.machine_id} Job {self.job_id}>"
