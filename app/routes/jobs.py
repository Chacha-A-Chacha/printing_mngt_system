# routes/jobs.py
from datetime import datetime
from sqlalchemy import and_

from flask import request, jsonify
from . import jobs_bp
from app import logger
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
      "pricing_input": 23400, // Base pricing input if not using unit-based pricing
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
    logger.info("Received data: %s", data)

    # 1. Validate the incoming data using the JobCreateSchema
    schema = JobCreateSchema()
    validated_data = None
    try:
        validated_data = schema.load(data)
        logger.info("Validated data: %s", validated_data)
    except Exception as e:  # more specifically, marshmallow.ValidationError
        logger.error("Unexpected error: %s", str(e))
        return jsonify({"errors": str(e)}), 400

    # 2. Find or create the client by phone number (via a dedicated client service)
    try:
        client = find_or_create_client(
            validated_data["client_name"],
            validated_data["client_phone_number"]
        )
        logger.info("Client found/created: %s", client)
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

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
    logger.info("Creation data: %s", creation_data)

    # 4. Use the JobService to create the job (and optionally handle immediate expenses).
    try:
        job, expenses_recorded = JobService.create_job(creation_data)
        logger.info("Job created: %s", job)
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
    data = request.get_json() or {}
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
    Now expects a JSON object with 'jobId' and 'expenses' array.

    Example Payload:
    {
      "jobId": 3,
      "expenses": [
        {
          "name": "Ink cartridges",
          "cost": 200.0,
          "shared": true,
          "job_ids": [4]
        }
      ]
    }
    """
    # 1. Parse the JSON. Expect an object with 'jobId' and 'expenses'
    data = request.get_json() or {}
    # logger.info(data)
    expense_data = data.get("expenses", [])
    if not isinstance(expense_data, list):
        return jsonify({"error": "Expected 'expenses' to be a list"}), 400
    # job_id_in_payload = body.get("jobId")
    # expenses_data = body.get("expenses", [])

    # (Optional) Check if job_id_in_payload matches the URL job_id
    # If you want to enforce this match, do so here:
    # if job_id_in_payload and job_id_in_payload != job_id:
    #     return jsonify({"error": "jobId in payload does not match URL"}), 400

    # 2. Validate the expenses array
    schema = ExpenseSchema(many=True)
    try:
        validated_expenses = schema.load(expense_data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # 3. Retrieve the main job from the URL
    job = Job.query.get_or_404(job_id)

    # 4. For each validated expense, allocate via ExpenseService
    allocated_expenses = []
    try:
        for exp_data in validated_expenses:
            expense_records = ExpenseService.allocate_expenses(job, exp_data)
            allocated_expenses.extend(expense_records)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    return jsonify({
        "message": "Expenses added successfully",
        "expenses": allocated_expenses
    }), 200


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
    logger.info(data)

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
        logger.info()
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
    logger.info(data)
    schema = JobTimeframeUpdateSchema()

    # 1. Validate timeframe data
    try:
        validated_data = schema.load(data)
    except ValidationError as err:
        logger.error(err)
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

    # (C) Attach material usages
    usage_list = []
    for usage_record in job.material_usages:
        # If we have usage_record.to_dict(), we can call it:
        if hasattr(usage_record, "to_dict"):
            usage_list.append(usage_record.to_dict())
        else:
            # fallback if to_dict not defined
            usage_list.append({
                "id": usage_record.id,
                "material_id": usage_record.material_id,
                "usage_meters": usage_record.usage_meters,
                "cost": usage_record.cost
            })
    job_data["material_usages"] = usage_list

    return jsonify(job_data), 200


class JobListSchema:
    def dump(self, jobs):
        pass


@jobs_bp.route("/list_jobs", methods=["GET"])
def list_jobs():
    """
    List jobs in a summary format.
    Optional query parameters can be used for filtering or pagination.
    Returns a JSON array of partial job data.

    Example Response:
    [
      {
        "id": 1,
        "description": "Banner printing",
        "job_type": "in_house",
        "progress_status": "in_progress",
        "total_cost": 120.0,
        "client_name": "John Doe"
      },
      ...
    ]
    """
    # (Optional) Implement filtering, e.g., by progress_status or job_type
    query = Job.query

    # Example: If you want to filter by status
    status_filter = request.args.get("status")
    if status_filter:
        query = query.filter_by(progress_status=status_filter)

    # Example: If you want pagination
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    jobs = pagination.items  # the jobs on this page

    # Use the partial schema for summary data
    schema = JobListSchema(many=True)
    try:
        job_list_data = schema.dump(jobs)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    return jsonify({
        "jobs": job_list_data,
        "page": page,
        "per_page": per_page,
        "total": pagination.total
    }), 200


@jobs_bp.route("/jobs/summary", methods=["GET"])
def list_jobs_summary():
    """
    Retrieve filtered and paginated jobs from the database.

    Query Parameters:
    - page: Current page number (default: 1)
    - limit: Items per page (default: 10)
    - jobType: Filter by job type (in_house/outsourced)
    - progressStatus: Filter by progress status
    - startDate: Filter jobs after this date (ISO format)
    - endDate: Filter jobs before this date (ISO format)
    """
    # Get query parameters with defaults
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    job_type = request.args.get('jobType')
    progress_status = request.args.get('progressStatus')
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    # Start with base query
    query = Job.query

    # Apply filters if provided
    filters = []
    if job_type and job_type != 'all':
        filters.append(Job.job_type == job_type)
    if progress_status and progress_status != 'all':
        filters.append(Job.progress_status == progress_status)
    if start_date:
        filters.append(Job.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        filters.append(Job.created_at <= datetime.fromisoformat(end_date))

    if filters:
        query = query.filter(and_(*filters))

    # Execute query with pagination
    paginated_jobs = query.paginate(
        page=page,
        per_page=limit,
        error_out=False
    )

    # Construct response
    job_list = []
    for job in paginated_jobs.items:
        client_name = job.client.name if job.client else None
        job_list.append({
            "id": job.id,
            "client_name": client_name,
            "progress_status": job.progress_status,
            "job_type": job.job_type,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "payment_status": job.payment_status
        })

    # Return paginated response
    return jsonify({
        "jobs": job_list,
        "pagination": {
            "currentPage": page,
            "totalPages": paginated_jobs.pages,
            "totalItems": paginated_jobs.total,
            "itemsPerPage": limit
        }
    }), 200
