# routes/jobs.py


from flask import request, jsonify
from . import jobs_bp
from ..models.in_house_printing import Material
from ..models.job import Job
from ..schemas.job_schemas import JobProgressUpdateSchema, \
    JobMaterialSchema, JobCreateSchema, ExpenseSchema, JobTimeframeUpdateSchema
from ..services.job_service_v2 import MaterialService, MachineUsageService, JobService, JobProgressService, \
    JobMaterialService, JobExpenseService, JobTimeframeService, ExpenseService
from ..services.client_service import find_or_create_client
from marshmallow import ValidationError


@jobs_bp.route("/jobs", methods=["POST"])
def create_job():
    """
    Create a new job with minimal required fields.
    Depending on 'job_type' (in_house/outsourced), certain fields become relevant:
    - 'in_house': Add material usage via /jobs/<job_id>/materials later.
    - 'outsourced': Provide vendor details (vendor_name, vendor_cost_per_unit, etc.).

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

    # 1. Validate the incoming data using the JobCreateSchema
    schema = JobCreateSchema()
    validated_data = None
    try:
        validated_data = schema.load(data)
    except Exception as e:  # more specifically, marshmallow.ValidationError
        return jsonify({"errors": str(e)}), 400

    # 2. Find or create the client by phone number (via a dedicated client service)
    client = find_or_create_client(
        validated_data["client_name"],
        validated_data["client_phone_number"]
    )

    # 3. Construct the creation payload for JobService
    #    We only store the client_id here, as the JobService expects it.
    creation_data = {
        "client_id": client.id,
        "description": validated_data["description"],
        "job_type": validated_data.get("job_type", "in_house"),
        "vendor_name": validated_data.get("vendor_name"),
        "vendor_cost_per_unit": validated_data.get("vendor_cost_per_unit", 0.0),
        "total_units": validated_data.get("total_units", 0),
        "pricing_per_unit": validated_data.get("pricing_per_unit", 0.0),
        "progress_status": validated_data.get("progress_status", "pending"),
        "timeframe": validated_data.get("timeframe", {}),
        "pricing_input": validated_data.get("pricing_input", 0.0),
        "expenses": validated_data.get("expenses", [])
    }

    # 4. Use the JobService to create the job (and optionally handle immediate expenses).
    try:
        job, expenses_recorded = JobService.create_job(creation_data)
        # If your JobService doesn't handle expenses, you could call:
        #   ExpenseService.allocate_expenses(job, validated_data["expenses"])
        #   job.save()
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    return jsonify({
        "message": "Job created successfully!",
        "job_id": job.id
    }), 201


@jobs_bp.route("/jobs/<int:job_id>/materials", methods=["POST"])
def add_job_materials(job_id):
    """
    Add or update material usage for an in-house job.
    Expects a list of material usage objects:
      [
        {
          "material_id": <int>,
          "usage_meters": <float>
        },
        ...
      ]

    Returns 400 if validation fails or job type is incorrect.
    Returns 200 with a message and job_id on success.
    """
    # 1. Parse and Validate the incoming JSON array via MaterialUsageSchema
    data = request.get_json() or []
    schema = JobMaterialSchema(many=True)  # we expect a list of usage records

    try:
        validated_materials = schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # 2. Fetch the job
    job = Job.query.get_or_404(job_id)

    # 3. Delegate logic to the JobMaterialService
    #    We'll handle each material usage entry in a loop or as a bulk update
    try:
        for usage_data in validated_materials:
            # usage_data = { "material_id": ..., "usage_meters": ... }
            JobMaterialService.update(job, usage_data)
    except ValueError as ve:
        # e.g., "Material not found" or "Insufficient material stock," or "job_type mismatch"
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        # Catch unexpected errors
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

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
    # 1. Load & validate the incoming JSON array using an expense schema
    data = request.get_json() or []
    schema = ExpenseSchema(many=True)  # expect a list of expense objects

    try:
        validated_expenses = schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # 2. Retrieve the main job
    job = Job.query.get_or_404(job_id)

    # 3. Delegate to the ExpenseService (allocate_expense or allocate_expenses)
    allocated_expenses = []
    try:
        for exp_data in validated_expenses:
            expense_records = ExpenseService.allocate_expenses(job, exp_data)
            allocated_expenses.extend(expense_records)
    except ValueError as ve:
        # e.g., shared expense references a non-existent job, etc.
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

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
    data = request.get_json() or {}

    # 1. Validate progress fields
    schema = JobProgressUpdateSchema()
    try:
        validated_data = schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # 2. Get job
    job = Job.query.get_or_404(job_id)

    # 3. Update via JobProgressService
    try:
        updated_job = JobProgressService.update(job, validated_data)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    return jsonify({"message": "Job progress updated", "job": updated_job.to_dict()}), 200


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
    data = request.get_json() or {}
    schema = JobTimeframeUpdateSchema()

    # 1. Validate timeframe data
    try:
        validated_data = schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # 2. Get job
    job = Job.query.get_or_404(job_id)

    # 3. Delegate to JobTimeframeService
    try:
        updated_job = JobTimeframeService.update(job, validated_data)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    return jsonify({"message": "Job timeframe updated", "job": updated_job.to_dict()}), 200


@jobs_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_job_detail(job_id):
    """
    Fetches the details of a single job, including:
      - Core Job fields (id, description, job_type, etc.)
      - Associated Client info
      - Job Expenses

    JSON Response Example:
    {
      "id": 101,
      "description": "Large banner printing",
      "job_type": "in_house",
      "total_cost": 250.0,
      ... other Job fields ...,
      "client": {
        "id": 10,
        "name": "Jane Doe",
        "phone_number": "555-1234",
        ...
      },
      "expenses": [
        {
          "id": 12,
          "name": "Ink cartridges",
          "cost": 30.0
          ...
        },
        ...
      ]
    }
    """
    job = Job.query.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Start with the job’s dictionary representation
    job_data = job.to_dict()

    # 1. Add the Client info, if present.
    #    Assuming client has a `.to_dict()` method or we build one.
    if job.client:
        job_data["client"] = job.client.to_dict()
        # If no to_dict exists, do something like:
        # job_data["client"] = {
        #     "id": job.client.id,
        #     "name": job.client.name,
        #     "phone_number": job.client.phone_number,
        #     ...
        # }
    else:
        job_data["client"] = None

    # 2. Add the Expenses as a list of dicts
    #    Assuming each expense has a `.to_dict()`.
    #    If not, we can inline a quick dict representation here.
    expense_list = []
    for exp in job.expenses:
        if hasattr(exp, "to_dict"):
            expense_list.append(exp.to_dict())
        else:
            # Minimal inline representation:
            expense_list.append({
                "id": exp.id,
                "name": exp.name,
                "cost": exp.cost,
                "date": exp.date.isoformat() if exp.date else None,
                "category": exp.category,
                "receipt_url": exp.receipt_url
            })

    job_data["expenses"] = expense_list

    return jsonify(job_data), 200
