from app import db
from . import BaseModel
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship


class Job(BaseModel):
    __tablename__ = 'jobs'

    client_id = Column(Integer, nullable=True)  # Adjust if referencing a client table
    description = Column(Text, nullable=False)
    progress_status = Column(String(50), default="pending")
    total_cost = Column(Float, default=0.0)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    last_status_change = Column(DateTime, nullable=True)

    expenses = relationship("JobExpense", backref="job", lazy='dynamic')
    notes = relationship("JobNote", backref="job", lazy='dynamic')
    material_usages = relationship("JobMaterialUsage", backref="job", lazy='dynamic')
    timeframe_logs = relationship("JobTimeframeChangeLog", backref="job", lazy='dynamic')

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "description": self.description,
            "progress_status": self.progress_status,
            "total_cost": self.total_cost,
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
