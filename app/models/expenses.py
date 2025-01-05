from . import BaseModel
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship


class JobExpense(BaseModel):
    __tablename__ = 'job_expenses'

    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    name = Column(String(200), nullable=False)
    cost = Column(Float, nullable=False)
    date = Column(DateTime, default=func.now())
    category = Column(String(100), nullable=True)
    receipt_url = Column(Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'cost': self.cost,
            'date': self.date,
            'category': self.category,
            'created_at': self.created_at,
        }
