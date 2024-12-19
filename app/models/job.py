from sqlalchemy import Enum

from app import db
from . import BaseModel
from .in_house_printing import Material
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship


class Job(BaseModel):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    client = relationship('Client', backref=db.backref('jobs', lazy=True))

    # Job lifecycle fields
    description = Column(Text, nullable=False)
    progress_status = Column(String(50), default="pending")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    last_status_change = Column(DateTime, nullable=True)

    # Costing and payment fields
    total_cost = Column(Float, default=0.0)          # Internal cost of the job
    total_amount = Column(Float, nullable=False, default=0.0)   # Amount to be charged to the client
    amount_paid = Column(Float, nullable=False, default=0.0)
    payment_status = Column(Enum('Paid', 'Partially Paid', 'Unpaid', name='payment_status'),
                            nullable=False, default='Unpaid')
    total_profit = Column(Float, nullable=True)  # Possibly total_amount - total_cost

    expenses = relationship("JobExpense", backref="job", lazy='dynamic')
    notes = relationship("JobNote", backref="job", lazy='dynamic')
    material_usages = relationship("JobMaterialUsage", backref="job", lazy='dynamic')
    timeframe_logs = relationship("JobTimeframeChangeLog", backref="job", lazy='dynamic')
    # If machine_readings relationship exists, it can be added here:
    # machine_readings = relationship("MachineReading", backref="job", lazy='dynamic')

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
        # Update total_profit if it depends on the payment state
        # For example, total_profit could be recalculated after changes to total_cost or total_amount
        if self.total_cost is not None:
            self.total_profit = self.total_amount - self.total_cost

        self.save()

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "description": self.description,
            "progress_status": self.progress_status,
            "total_cost": self.total_cost,
            "total_amount": self.total_amount,
            "amount_paid": self.amount_paid,
            "payment_status": self.payment_status,
            "total_profit": self.total_profit,
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "cancellation_reason": self.cancellation_reason,
            "last_status_change": self.last_status_change.isoformat() if self.last_status_change else None
        }


class JobNote(BaseModel):
    __tablename__ = 'job_notes'

    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    note = Column(Text, nullable=False)


class JobMaterialUsage(BaseModel):
    __tablename__ = 'job_material_usages'

    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    usage_meters = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)


class JobTimeframeChangeLog(BaseModel):
    __tablename__ = 'job_timeframe_change_logs'

    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    old_start_date = Column(Date, nullable=True)
    old_end_date = Column(Date, nullable=True)
    reason = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=func.now())
