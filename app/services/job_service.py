# services/job_service.py
from datetime import datetime
from app.models.in_house_printing import Material, MachineReading, Job


class MaterialService:
    @staticmethod
    def check_stock_levels():
        low_stock_materials = Material.query.filter(Material.stock_level < Material.min_threshold).all()
        return low_stock_materials

    @staticmethod
    def deduct_material_usage(material_id, usage_amount):
        material = Material.query.get(material_id)
        if material:
            material.stock_level -= usage_amount
            material.save()


class MachineUsageService:
    @staticmethod
    def calculate_material_usage(start_meter, end_meter, material_margin=0.05):
        total_meters = end_meter - start_meter
        material_usage = total_meters * (1 + material_margin)
        return material_usage

    @staticmethod
    def log_machine_usage(job_id, start_meter, end_meter, material_id):
        material_usage = MachineUsageService.calculate_material_usage(start_meter, end_meter)
        MachineReading(
            job_id=job_id,
            start_meter=start_meter,
            end_meter=end_meter,
            material_usage=material_usage
        ).save()

        MaterialService.deduct_material_usage(material_id, material_usage)
        return material_usage


class JobService:
    @classmethod
    def create_job(cls, data):
        with db.session.begin():
            job = cls._create_job_record(data)
            cls._handle_material_usage(job, data)
            expenses_recorded = cls._process_expenses(job, data)
            # job.total_cost already updated during process_expenses
            return job, expenses_recorded

    @classmethod
    def _create_job_record(cls, data):
        job = Job(
            client_id=data["client_id"],
            description=data["description"],
            progress_status=data["progress_status"],
        )
        # Handle timeframe
        timeframe = data.get("timeframe", {})
        if "start" in timeframe:
            job.start_date = timeframe["start"]
        if "end" in timeframe:
            job.end_date = timeframe["end"]
            if job.start_date and job.end_date and job.start_date > job.end_date:
                raise ValueError("Start date cannot be after end date.")

        # Initial total cost
        job.total_cost = data["pricing_input"]
        job.save()
        return job

    @classmethod
    def _handle_material_usage(cls, job, data):
        material_id = data.get("material_id")
        usage = data.get("material_usage_meters", 0)
        if material_id and usage > 0:
            material = Material.query.get(material_id)
            if not material:
                raise ValueError("Material not found.")
            if material.stock_level < usage:
                raise ValueError("Insufficient material stock.")

            material.stock_level -= usage
            material.save()

            cost_of_material = (material.cost_per_sq_meter or 0) * usage
            job.total_cost += cost_of_material
            job.save()

    @classmethod
    def _process_expenses(cls, job, data):
        expenses = data.get("expenses", [])
        return ExpenseService.allocate_expenses(job, expenses)


class ExpenseService:
    @classmethod
    def allocate_expenses(cls, job, expenses):
        allocated_expenses = []
        for expense_data in expenses:
            expense_records = cls._allocate_expense(job, expense_data)
            allocated_expenses.extend(expense_records)
        return allocated_expenses

    @classmethod
    def _allocate_expense(cls, primary_job, expense):
        name = expense["name"]
        cost = expense["cost"]
        shared = expense.get("shared", False)
        specified_job_ids = expense.get("job_ids", [])

        if shared:
            if specified_job_ids:
                # Associate expense with specified jobs + primary job (if not included)
                all_job_ids = set(specified_job_ids)
                all_job_ids.add(primary_job.id)
            else:
                # No job_ids given, only allocate to primary job
                all_job_ids = {primary_job.id}
        else:
            # Not shared: only current job
            all_job_ids = {primary_job.id}

        allocated_records = []
        for jid in all_job_ids:
            linked_job = Job.query.get(jid)
            if not linked_job:
                raise ValueError(f"Job with id {jid} not found for expense assignment.")

            new_expense = JobExpense(job_id=jid, name=name, cost=cost)
            new_expense.save()

            # Update total cost if expense belongs to the primary job
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


class JobProgressService:
    @classmethod
    def update(cls, job, data):
        previous_status = job.progress_status
        new_status = data['progress_status']

        allowed_transitions = {
            "pending": ["in_progress", "cancelled"],
            "in_progress": ["on_hold", "completed", "cancelled"],
            "on_hold": ["in_progress", "cancelled"],
            "completed": ["in_progress"],  # allow reopening if desired
            "cancelled": []
        }

        if new_status not in allowed_transitions.get(previous_status, []):
            raise ValueError(f"Invalid status transition from {previous_status} to {new_status}")

        job.progress_status = new_status
        job.last_status_change = datetime.now()

        if new_status == "completed":
            job.completed_at = data.get('completed_at', datetime.now())
            cls._handle_job_completion(job)
        elif new_status == "cancelled":
            job.cancelled_at = datetime.now()
            job.cancellation_reason = data.get('reason_for_status_change')

        if data.get('notes'):
            cls._add_job_note(job, data['notes'])

        db.session.commit()
        return job

    @classmethod
    def _handle_job_completion(cls, job):
        # additional logic on job completion (e.g., notifications, billing)
        pass

    @classmethod
    def _add_job_note(cls, job, note):
        job_note = JobNote(
            job_id=job.id,
            note=note,
            created_at=datetime.now()
        )
        db.session.add(job_note)
        db.session.commit()


class JobMaterialService:
    @classmethod
    def update(cls, job, data):
        material_id = data['material_id']
        additional_usage = data['additional_usage_meters']

        material = Material.query.get_or_404(material_id)
        if material.stock_level < additional_usage:
            raise ValueError("Insufficient material stock")

        material.stock_level -= additional_usage
        db.session.commit()  # commit material update

        # Calculate added material cost
        added_cost = (material.cost_per_sq_meter or 0) * additional_usage
        job.total_cost += added_cost

        material_usage = JobMaterialUsage(
            job_id=job.id,
            material_id=material.id,
            usage_meters=additional_usage,
            cost=added_cost
        )
        db.session.add(material_usage)
        db.session.commit()
        return job


class JobExpenseService:
    @classmethod
    def update(cls, job, data):
        expenses = data['expenses']
        total_expense = 0
        for exp_data in expenses:
            expense = JobExpense(
                job_id=job.id,
                name=exp_data['name'],
                cost=exp_data['cost'],
                date=exp_data.get('date', datetime.now()),
                category=exp_data.get('category'),
                receipt_url=exp_data.get('receipt_url')
            )
            db.session.add(expense)
            total_expense += exp_data['cost']

        job.total_cost += total_expense
        db.session.commit()
        return job


class JobTimeframeService:
    @classmethod
    def update(cls, job, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        # Validate date changes
        if start_date:
            job.start_date = start_date
        if end_date:
            if job.start_date and end_date < job.start_date:
                raise ValueError("End date cannot be before start date")
            job.end_date = end_date

        if data.get('reason_for_change'):
            cls._log_timeframe_change(job, data['reason_for_change'])

        db.session.commit()
        return job

    @classmethod
    def _log_timeframe_change(cls, job, reason):
        change_log = JobTimeframeChangeLog(
            job_id=job.id,
            old_start_date=job.start_date,
            old_end_date=job.end_date,
            reason=reason,
            changed_at=datetime.now()
        )
        db.session.add(change_log)
        db.session.commit()
