from datetime import datetime

from .. import db, logger
from ..models.expenses import JobExpense
from ..models.in_house_printing import Material
from ..models.job import (
    Job,
    JobNote,
    JobMaterialUsage,
    JobTimeframeChangeLog, JobProgressStatus
)
from ..models.machine import MachineReading


class MaterialService:
    """
    Manages stock checks and usage deductions for materials.
    Typically used by the material-specific update route
    (/jobs/<job_id>/materials).
    """

    @staticmethod
    def check_stock_levels():
        """
        Returns a list of materials whose stock_level is
        below their min_threshold.
        """
        return Material.query.filter(Material.stock_level < Material.min_threshold).all()

    @staticmethod
    def deduct_material_usage(material_id, usage_amount):
        """
        Deducts the specified usage_amount from the material’s stock_level.
        The caller should handle any checks (e.g., if stock is sufficient).
        """
        material = Material.query.get(material_id)
        if material:
            material.stock_level -= usage_amount
            material.save()


class MachineUsageService:
    """
    Example service for logging machine usage (start_meter, end_meter),
    calculating actual material usage, and deducting from stock accordingly.
    """

    @staticmethod
    def calculate_material_usage(start_meter, end_meter, material_margin=0.05):
        """
        Demonstrates how usage might be calculated from machine meter readings,
        plus an optional margin factor.
        """
        total_meters = end_meter - start_meter
        material_usage = total_meters * (1 + material_margin)
        return material_usage

    @staticmethod
    def log_machine_usage(job_id, start_meter, end_meter, material_id):
        """
        Creates a MachineReading record and deducts the relevant material usage
        from stock. Typically used in an advanced scenario where
        machine counters track usage.
        """
        from ..models.machine import MachineReading  # ensure correct import

        material_usage = MachineUsageService.calculate_material_usage(start_meter, end_meter)
        reading = MachineReading(
            job_id=job_id,
            start_meter=start_meter,
            end_meter=end_meter,
            material_usage=material_usage
        )
        reading.save()

        MaterialService.deduct_material_usage(material_id, material_usage)
        return material_usage


class ExpenseService:
    """
    Handles expense allocation. The job creation or job update code can call
    `allocate_expenses` if immediate expenses are supplied.
    Otherwise, they may be added later via a dedicated route.
    """

    @classmethod
    def allocate_expenses(cls, job, expenses):
        """
        Iterates over the provided expense data,
        calling _allocate_expense for each item.
        """
        allocated_expenses = []
        expense_list = [expenses] if isinstance(expenses, dict) else expenses

        for expense_data in expense_list:
            expense_records = cls._allocate_expense(job, expense_data)
            allocated_expenses.extend(expense_records)
        return allocated_expenses

    @classmethod
    def _allocate_expense(cls, primary_job, expense):
        """
        Handles shared vs. non-shared expenses. If 'shared' is true and job_ids
        are provided, creates expense entries for each job. Also updates
        primary_job.total_cost if the expense is allocated to it.
        """
        name = expense["name"]
        cost = expense["cost"]
        shared = expense.get("shared", False)
        specified_job_ids = expense.get("job_ids", [])

        if shared:
            if specified_job_ids:
                all_job_ids = set(specified_job_ids)
                all_job_ids.add(primary_job.id)
            else:
                all_job_ids = {primary_job.id}
        else:
            all_job_ids = {primary_job.id}

        allocated_records = []
        for jid in all_job_ids:
            linked_job = Job.query.get(jid)
            if not linked_job:
                raise ValueError(f"Job with id {jid} not found for expense assignment.")

            new_expense = JobExpense(job_id=jid, name=name, cost=cost)
            new_expense.save()

            if jid == primary_job.id:
                primary_job.total_cost += cost
                primary_job.save()

            allocated_records.append({
                "expense_id": new_expense.id,
                "name": name,
                "cost": cost,
                "job_id": jid
            })

        return allocated_records


class JobService:
    """
    Handles creating a job with minimal data.
    Material usage is now separate, so there's no _handle_material_usage call here.
    """

    @classmethod
    def create_job(cls, data):
        """
        Creates a new job within a transaction.
        Optionally processes expenses if included in the creation payload.
        """
        try:
            job = cls._create_job_record(data)
            expenses_recorded = cls._process_expenses(job, data)
            return job, expenses_recorded
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            db.session.rollback()
            raise e

    @classmethod
    def _create_job_record(cls, data):
        """
        Builds a Job object from the provided data,
        including job_type fields if relevant (e.g., vendor_name, vendor_cost_per_unit, etc.).
        """
        job = Job(
            client_id=data["client_id"],
            description=data["description"],
            # Keep or set an initial progress_status
            progress_status=data.get("progress_status", "pending"),

            # Additional fields for in-house vs. outsourced
            job_type=data.get("job_type", "in_house"),
            vendor_name=data.get("vendor_name"),
            vendor_cost_per_unit=data.get("vendor_cost_per_unit", 0.0),
            total_units=data.get("total_units", 0),
            pricing_per_unit=data.get("pricing_per_unit", 0.0)
        )

        # Timeframe
        timeframe = data.get("timeframe", {})
        if "start" in timeframe:
            job.start_date = timeframe["start"]
        if "end" in timeframe:
            job.end_date = timeframe["end"]
            if job.start_date and job.end_date and job.start_date > job.end_date:
                raise ValueError("Start date cannot be after end date.")

        # total_cost can be partially initialized if you want
        # (e.g., from pricing_input) or left at 0.0.
        job.total_cost = data.get("pricing_input", 0.0)
        job.save()
        return job

    @classmethod
    def _process_expenses(cls, job, data):
        """
        If the creation payload includes expense data, allocate them now.
        Otherwise, an empty list of expenses is returned.
        """
        expenses = data.get("expenses", [])
        return ExpenseService.allocate_expenses(job, expenses)


class JobProgressService:
    """
    Allows partial updates to the job's progress status.
    For example, from 'pending' to 'in_progress', or 'in_progress' to 'completed'.
    """

    @classmethod
    def update(cls, job: Job, data: dict):
        """
        Update job progress with validation rules.

        Args:
            job: Job instance to update
            data: Validated data dictionary containing update fields

        Returns:
            Updated Job instance

        Raises:
            ValueError: If status transition is invalid
        """
        previous_status = job.progress_status
        new_status = JobProgressStatus(data['progress_status'])

        # Define allowed transitions based on JobProgressStatus enum
        allowed_transitions = {
            JobProgressStatus.PENDING: [
                JobProgressStatus.IN_PROGRESS,
                JobProgressStatus.CANCELLED
            ],
            JobProgressStatus.IN_PROGRESS: [
                JobProgressStatus.ON_HOLD,
                JobProgressStatus.COMPLETED,
                JobProgressStatus.CANCELLED
            ],
            JobProgressStatus.ON_HOLD: [
                JobProgressStatus.IN_PROGRESS,
                JobProgressStatus.CANCELLED
            ],
            JobProgressStatus.COMPLETED: [
                JobProgressStatus.IN_PROGRESS  # Allow reopening if business logic requires
            ],
            JobProgressStatus.CANCELLED: []  # No transitions allowed from cancelled
        }

        if new_status not in allowed_transitions.get(previous_status, []):
            raise ValueError(
                f"Invalid status transition from {previous_status.value} to {new_status.value}. "
                f"Valid transitions are: {[s.value for s in allowed_transitions[previous_status]]}"
            )

        job.progress_status = new_status
        job.last_status_change = datetime.now()

        if new_status == JobProgressStatus.COMPLETED:
            job.completed_at = data.get('completed_at', datetime.now())
            cls._handle_job_completion(job)
        elif new_status == JobProgressStatus.CANCELLED:
            job.cancelled_at = datetime.now()
            job.cancellation_reason = data.get('reason_for_status_change')
            if not job.cancellation_reason:
                raise ValueError("Reason is required when cancelling a job")

        if data.get('notes'):
            cls._add_job_note(job, data['notes'])

        job.save()
        return job

    @classmethod
    def _handle_job_completion(cls, job: Job):
        """
        Additional completion logic could go here,
        e.g., finalize billing or send completion notifications.
        """
        pass

    @classmethod
    def _add_job_note(cls, job: Job, note: str):
        """
        Records a note about the status update
        (e.g., reason for on_hold, or message upon completion).
        """
        job_note = JobNote(
            job_id=job.id,
            note=note
        )
        job_note.save()


class JobMaterialService:
    """

    Updates job material usage for in-house jobs.
    Typically invoked by /jobs/<job_id>/materials route.

    """

    @classmethod
    def update(cls, job, data):
        """
        data = {
          'material_id': <int>,
          'usage_meters': <float>
        }
        """
        material_id = data['material_id']
        additional_usage = data['usage_meters']

        # Check if job_type is 'in_house'; if outsourced, might raise an error or do nothing.
        if job.job_type == 'outsourced':
            raise ValueError("Cannot add material usage to an outsourced job.")

        material = Material.query.get(material_id)
        if not material:
            raise ValueError("Material not found.")
        if material.stock_level < additional_usage:
            raise ValueError("Insufficient material stock")

        # Deduct stock, update cost
        material.stock_level -= additional_usage
        material.save()

        added_cost = (material.cost_per_sq_meter or 0) * additional_usage
        job.total_cost += added_cost

        # Create a usage record
        material_usage = JobMaterialUsage(
            job_id=job.id,
            material_id=material.id,
            usage_meters=additional_usage,
            cost=added_cost
        )
        material_usage.save()
        job.save()
        return job


class JobExpenseService:
    """
    Adds or updates job expenses after creation.
    Typically used in a partial update route like /jobs/<job_id>/expenses.
    """

    @classmethod
    def update(cls, job, data):
        """
        data = {
          'expenses': [
             { 'name': 'Extra labor', 'cost': 100.0, 'date': <date>, 'category': ..., 'receipt_url': ... },
             ...
          ]
        }
        """
        expenses = data['expenses']
        total_expense = 0
        for exp_data in expenses:
            new_expense = JobExpense(
                job_id=job.id,
                name=exp_data['name'],
                cost=exp_data['cost'],
                date=exp_data.get('date', datetime.now()),
                category=exp_data.get('category'),
                receipt_url=exp_data.get('receipt_url')
            )
            new_expense.save()
            total_expense += exp_data['cost']

        job.total_cost += total_expense
        job.save()
        return job


class JobTimeframeService:
    """
    Updates the timeframe (start_date, end_date) for a job,
    and logs changes in JobTimeframeChangeLog if needed.
    """

    @classmethod
    def update(cls, job, data):
        """
        data = {
          'start_date': <date or None>,
          'end_date': <date or None>,
          'reason_for_change': <string or None>
        }
        """
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date:
            job.start_date = start_date
        if end_date:
            if job.start_date and end_date < job.start_date:
                raise ValueError("End date cannot be before start date")
            job.end_date = end_date

        if data.get('reason_for_change'):
            cls._log_timeframe_change(job, data['reason_for_change'])

        job.save()
        return job

    @classmethod
    def _log_timeframe_change(cls, job, reason):
        """
        Creates a JobTimeframeChangeLog record reflecting the old timeframe
        and the reason for the change.
        """
        change_log = JobTimeframeChangeLog(
            job_id=job.id,
            old_start_date=job.start_date,
            old_end_date=job.end_date,
            reason=reason
        )
        change_log.save()
