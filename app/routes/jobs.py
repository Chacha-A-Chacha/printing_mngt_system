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
