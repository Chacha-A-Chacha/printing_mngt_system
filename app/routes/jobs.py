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
