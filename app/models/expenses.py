# models/expenses.py
from . import BaseModel
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from .. import db

class JobExpense(BaseModel):
    __tablename__ = 'job_expenses'

    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    name = Column(String(200), nullable=False)
    cost = Column(Float, nullable=False)
    date = Column(DateTime, default=func.now())
    category = Column(String(100), nullable=True)
    receipt_url = Column(Text, nullable=True)

    # Add the relationship to Job
    job = relationship('Job', backref=db.backref('expenses', lazy='dynamic'))

    def serialize(self):  # Changed from to_dict for consistency
        return {
            'id': self.id,
            'job_id': self.job_id,
            'name': self.name,
            'cost': self.cost,
            'date': self.date.isoformat(),
            'category': self.category,
            'receipt_url': self.receipt_url,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
