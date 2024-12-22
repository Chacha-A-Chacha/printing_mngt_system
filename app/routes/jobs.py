# routes/jobs.py


from flask import request, jsonify
from . import jobs_bp
from .. import logger
from ..models.in_house_printing import Material
from ..models.job import Job
from ..models.client import Client
from ..models.machine import MachineReading
from ..schemas.job_schemas import JobProgressUpdateSchema, JobMaterialUpdateSchema, JobExpenseUpdateSchema, \
    JobTimeframeUpdateSchema
from ..services.job_service import MaterialService, MachineUsageService, JobService, JobProgressService, \
    JobMaterialService, JobExpenseService, JobTimeframeService
from ..utils.helpers import _determine_update_type
from ..validation import validate_job_input


@jobs_bp.route("/jobs", methods=["POST"])
def create_job():
    """
    Create a new job with minimal required fields.
    Depending on 'job_type' (in_house/outsourced), certain fields become relevant:
    - 'in_house': Might later add material usage via /jobs/<job_id>/materials
    - 'outsourced': Might specify vendor details (via 'vendor_name', 'vendor_cost_per_unit', etc.)

    JSON Payload (example):
    {
      "client_name": "John Doe",
      "client_phone_number": "555-1234",
      "description": "Merchandise printing",
      "job_type": "outsourced",
      "vendor_name": "ACME Printing",
      "vendor_cost_per_unit": 5.0,
      "total_units": 100,
      "pricing_per_unit": 10.0,
      "timeframe": {
        "start": "2024-01-01",
        "end": "2024-01-05"
      },
      "expenses": [
        {
          "name": "Design Fee",
          "cost": 50.0,
          "shared": false
        }
      ]
    }

    Response:
      201 Created
      {
        "message": "Job created successfully!",
        "job_id": <newly_created_job_id>
      }
    """
    data = request.get_json() or {}

    # Validate base job data (including job_type, client info, description, etc.)
    validated_data, errors = validate_job_input(data)  # e.g., using JobCreateSchema
    if errors:
        return jsonify({"errors": errors}), 400

    # 1. Find or create the client by phone number
    client = find_or_create_client(
        validated_data['client_name'],
        validated_data['client_phone_number']
    )

    # 2. Build the Job model, setting in-house/outsourced fields as needed
    #    For example, if 'job_type' == 'outsourced', we can store vendor_name, etc.
    job = Job(
        client_id=client.id,
        description=validated_data['description'],
        job_type=validated_data.get('job_type', 'in_house'),
        vendor_name=validated_data.get('vendor_name'),
        vendor_cost_per_unit=validated_data.get('vendor_cost_per_unit', 0.0),
        total_units=validated_data.get('total_units', 0),
        pricing_per_unit=validated_data.get('pricing_per_unit', 0.0),
        progress_status=validated_data.get('progress_status', 'pending')
    )

    # Optional: If you want to set an initial cost (e.g. pricing_input) at creation
    initial_pricing = validated_data.get('pricing_input', 0.0)
    job.total_cost = initial_pricing

    # 3. Handle timeframe if provided
    timeframe = validated_data.get('timeframe', {})
    if 'start' in timeframe:
        job.start_date = timeframe['start']
    if 'end' in timeframe:
        job.end_date = timeframe['end']

    # 4. Optionally handle immediate expenses
    #    You can use an ExpenseService or direct logic to add expenses here
    expenses = validated_data.get('expenses', [])
    for exp_data in expenses:
        # Example: create expense records, update job.total_cost, etc.
        pass

    # 5. Save the new job
    job.save()

    return jsonify({
        "message": "Job created successfully!",
        "job_id": job.id
    }), 201


@jobs_bp.route("/jobs/<int:job_id>/materials", methods=["POST"])
def add_job_materials(job_id):
    """
    Add or update material usage for an in-house job.
    This endpoint expects a list of materials with usage amounts.

    JSON Payload Example:
    [
      {
        "material_id": 10,
        "usage_meters": 20.0
      },
      {
        "material_id": 11,
        "usage_meters": 5.0
      }
    ]

    Response:
      200 OK
      {
        "message": "Materials added/updated successfully",
        "job_id": <job_id>
      }
    """
    job = Job.query.get_or_404(job_id)
    data = request.get_json() or []

    # Validate list of materials usage
    validated_materials, errors = validate_material_usage_input(data)
    if errors:
        return jsonify({"errors": errors}), 400

    # If the job is outsourced, material usage might be irrelevant or disallowed
    if job.job_type == 'outsourced':
        return jsonify({"error": "Cannot add material usage to an outsourced job."}), 400

    for mat_data in validated_materials:
        material = Material.query.get(mat_data['material_id'])
        if not material:
            return jsonify({"error": f"Material {mat_data['material_id']} not found"}), 404

        usage_meters = mat_data['usage_meters']
        if material.stock_level < usage_meters:
            return jsonify({"error": "Insufficient stock"}), 400

        # Deduct from stock and update job cost
        material.stock_level -= usage_meters
        material.save()

        cost_of_material = (material.cost_per_sq_meter or 0) * usage_meters
        job.total_cost += cost_of_material

        # Create a usage record
        usage_record = JobMaterialUsage(
            job_id=job.id,
            material_id=material.id,
            usage_meters=usage_meters,
            cost=cost_of_material
        )
        usage_record.save()

    job.save()
    return jsonify({"message": "Materials added/updated successfully", "job_id": job.id}), 200


@jobs_bp.route("/jobs/<int:job_id>/expenses", methods=["POST"])
def add_job_expenses(job_id):
    """
    Adds or updates expenses for a specific job.
    Supports shared expenses by referencing multiple job_ids if needed.

    JSON Payload Example:
    [
      {
        "name": "Ink cartridges",
        "cost": 30.0,
        "shared": false
      },
      {
        "name": "Electricity bill",
        "cost": 50.0,
        "shared": true,
        "job_ids": [124, 125]
      }
    ]

    Response:
      200 OK
      {
        "message": "Expenses added successfully",
        "expenses": [...]
      }
    """
    job = Job.query.get_or_404(job_id)
    data = request.get_json() or []

    # Validate the list of expenses
    validated_expenses, errors = validate_expenses_input(data)
    if errors:
        return jsonify({"errors": errors}), 400

    allocated_expenses = []
    for exp_data in validated_expenses:
        # If using an ExpenseService, or do inline logic:
        expense_records = ExpenseService.allocate_expense(job, exp_data)
        allocated_expenses.extend(expense_records)

    return jsonify({"message": "Expenses added successfully", "expenses": allocated_expenses}), 200


@jobs_bp.route("/jobs/<int:job_id>/progress", methods=["PATCH"])
def update_job_progress(job_id):
    """
    Updates the job’s progress status (pending, in_progress, on_hold, completed, cancelled).

    JSON Payload Example:
    {
      "progress_status": "in_progress",
      "notes": "Started production",
      "completed_at": null,
      "reason_for_status_change": null
    }

    Response:
      200 OK
      {
        "message": "Job progress updated",
        "job": { ...updated job data... }
      }
    """
    job = Job.query.get_or_404(job_id)
    data = request.get_json() or {}

    validated_data, errors = validate_progress_input(data)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        updated_job = JobProgressService.update(job, validated_data)
        return jsonify({"message": "Job progress updated", "job": updated_job.to_dict()}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@jobs_bp.route("/jobs/<int:job_id>/timeframe", methods=["PATCH"])
def update_job_timeframe(job_id):
    """
    Updates the start_date/end_date of the job and logs a reason for the change if provided.

    JSON Payload Example:
    {
      "start_date": "2024-01-02",
      "end_date": "2024-01-10",
      "reason_for_change": "Client requested extension"
    }

    Response:
      200 OK
      {
        "message": "Job timeframe updated",
        "job": { ...updated job data... }
      }
    """
    job = Job.query.get_or_404(job_id)
    data = request.get_json() or {}

    validated_data, errors = validate_timeframe_input(data)
    if errors:
        return jsonify({"errors": errors}), 400

    updated_job = JobTimeframeService.update(job, validated_data)
    return jsonify({"message": "Job timeframe updated", "job": updated_job.to_dict()}), 200


@jobs_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_job_detail(job_id):
    """
    Fetches the details of a single job, including client info and any relevant fields.
    JSON Response contains job.to_dict() data.

    Response:
      200 OK
      {
        "id": <job_id>,
        "description": "...",
        "job_type": "...",
        ...all other job fields...
      }
    """
    job = Job.query.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job.to_dict()), 200
