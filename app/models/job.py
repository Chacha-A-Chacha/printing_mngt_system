import enum

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, func, Enum
from sqlalchemy.orm import relationship
from app import db
from . import BaseModel
from .materials import Material  # Adjust import if needed
from .client import Client


class JobProgressStatus(enum.Enum):
    """
    Enum representing possible job progress statuses.
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Job(BaseModel):
    """
    Represents a printing job. This model now supports both:
    - In-House jobs: Rely on internal materials and production.
    - Outsourced jobs: Production is handled by external vendors.

    Key Points:
    1. job_type determines which cost fields are relevant:
       - 'in_house': cost mostly derived from JobMaterialUsage and other expenses.
       - 'outsourced': cost derived from vendor_cost_per_unit * total_units, plus expenses.

    2. vendor_ and unit-based fields apply primarily to outsourced jobs.
       They may remain NULL for in-house jobs.

    3. total_cost, total_amount, amount_paid, and total_profit track overall
       financials for the job. total_profit can be recalculated whenever cost or
       amount changes.

    4. payment_status tracks how much the client has paid relative to total_amount.
    """

    __tablename__ = 'jobs'

    # Primary Key

    # Linking to an existing client
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    client = relationship('Client', backref=db.backref('jobs', lazy=True))

    # Job Lifecycle Fields
    description = Column(Text, nullable=False, doc="A short description of the job.")
    progress_status = Column(
        Enum(JobProgressStatus),
        nullable=False,
        default=JobProgressStatus.PENDING,
        doc="Job progress status (e.g., 'pending', 'in_progress')."
    )
    start_date = Column(Date, nullable=True, doc="Scheduled start date for the job.")
    end_date = Column(Date, nullable=True, doc="Scheduled end date for the job.")
    completed_at = Column(DateTime, nullable=True, doc="Timestamp when the job was fully completed.")
    cancelled_at = Column(DateTime, nullable=True, doc="Timestamp if/when the job was cancelled.")
    cancellation_reason = Column(Text, nullable=True, doc="Reason for cancellation, if cancelled.")
    last_status_change = Column(DateTime, nullable=True, doc="Timestamp of the last status update.")

    # Job Type (In-house vs Outsourced)
    job_type = Column(Enum('in_house', 'outsourced', name='job_type'),
                      nullable=False,
                      default='in_house',
                      doc="Determines if the job is produced in-house or outsourced.")

    # Outsourced Fields (Relevant only if job_type == 'outsourced')
    vendor_name = Column(String(255), nullable=True, doc="Name of the external vendor handling production.")
    vendor_cost_per_unit = Column(Float, default=0.0, doc="Cost per piece/unit charged by the external vendor.")
    total_units = Column(Integer, default=0, doc="Number of units/pieces produced if outsourced.")
    pricing_per_unit = Column(Float, default=0.0, doc="Price charged to client per unit for outsourced jobs.")

    # Cost & Payment Tracking
    total_cost = Column(Float, default=0.0,
                        doc="Aggregate cost for the job (materials, vendor fees, expenses, etc.).")
    total_amount = Column(Float, nullable=False, default=0.0,
                          doc="Amount to be charged to the client (can be per-unit or a fixed sum).")
    amount_paid = Column(Float, nullable=False, default=0.0,
                         doc="How much the client has paid so far.")
    payment_status = Column(
        Enum('Paid', 'Partially Paid', 'Unpaid', name='payment_status'),
        nullable=False,
        default='Unpaid',
        doc="Payment status reflecting how much of total_amount has been covered."
    )
    total_profit = Column(Float, nullable=True,
                          doc="Calculated as total_amount - total_cost, or updated at runtime.")

    notes = relationship("JobNote", backref="job", lazy='dynamic',
                         doc="Notes or comments linked to the job.")
    timeframe_logs = relationship("JobTimeframeChangeLog", backref="job", lazy='dynamic',
                                  doc="History of changes to the job's timeframe.")

    def calculate_outstanding_amount(self):
        """
        Returns how much remains unpaid based on total_amount and amount_paid.
        """
        return self.total_amount - self.amount_paid

    def update_payment(self, payment_amount):
        """
        Add a specified payment amount to the job's amount_paid and update payment_status accordingly.
        Also recalculates total_profit if it is dependent on cost and amount.
        """
        self.amount_paid += payment_amount
        if self.amount_paid >= self.total_amount:
            self.payment_status = 'Paid'
        elif self.amount_paid > 0:
            self.payment_status = 'Partially Paid'
        else:
            self.payment_status = 'Unpaid'

        # Optionally recalc profit
        if self.total_cost is not None:
            self.total_profit = self.total_amount - self.total_cost

        self.save()

    def to_dict(self):
        """
        Serializes this Job into a Python dict, suitable for JSON responses.
        Fields like vendor_cost_per_unit, total_units, etc., will be null or 0 for in_house jobs.
        """
        return {
            "id": self.id,
            "client_id": self.client_id,
            "description": self.description,
            "job_type": self.job_type,
            "vendor_name": self.vendor_name,
            "vendor_cost_per_unit": self.vendor_cost_per_unit,
            "total_units": self.total_units,
            "pricing_per_unit": self.pricing_per_unit,
            "progress_status": self.progress_status.value,
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
    """
    Represents a note or comment associated with a job.
    Could be internal remarks, clarifications, or client feedback.
    """

    __tablename__ = 'job_notes'

    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    note = Column(Text, nullable=False, doc="The text content of this note.")


class JobTimeframeChangeLog(BaseModel):
    """
    Logs changes to the job's timeframe (start_date, end_date),
    allowing tracking of schedule alterations over the job's lifecycle.
    """

    __tablename__ = 'job_timeframe_change_logs'

    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    old_start_date = Column(Date, nullable=True, doc="Previous start date before change.")
    old_end_date = Column(Date, nullable=True, doc="Previous end date before change.")
    reason = Column(Text, nullable=True, doc="Explanation or comment about the timeframe change.")
    changed_at = Column(DateTime, default=func.now(), doc="Timestamp when this timeframe change was logged.")
