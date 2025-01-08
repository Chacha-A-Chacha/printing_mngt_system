# routes/in_house_printing.py

from flask import request, jsonify
from . import in_house_printing_bp
from .. import logger
from ..models.in_house_printing import Material
from ..models.job import Job
from ..models.client import Client
from ..models.machine import MachineReading
from ..schemas.job_schemas import JobProgressUpdateSchema, JobExpenseUpdateSchema, \
    JobTimeframeUpdateSchema
from ..services.job_service import MaterialService, MachineUsageService, JobService, JobProgressService, \
    JobMaterialService, JobExpenseService, JobTimeframeService
from ..utils.helpers import _determine_update_type
from ..validation import validate_job_input


# Route: List all materials
@in_house_printing_bp.route("/materials", methods=["GET"])
def list_materials():
    materials = Material.query.all()
    return jsonify([material.serialize() for material in materials]), 200


# Route: Create a new material
@in_house_printing_bp.route("/new_material", methods=["POST"])
def create_material():
    data = request.get_json() or {}
    name = data.get("name")
    material_type = data.get("type")

    # Validate required fields
    if not name or not material_type:
        return jsonify({"error": "Both 'name' and 'type' are required fields."}), 400

    # Check if a material with the same name and type exists
    existing_material = Material.query.filter_by(name=name, type=material_type).first()
    if existing_material:
        return jsonify({"error": "Material with this name and type already exists."}), 409

    # Create a new Material instance
    new_material = Material(
        name=name,
        type=material_type,
        stock_level=data.get("stock_level", 0),
        min_threshold=data.get("min_threshold", 0),  # Adjust or remove if not required
        cost_per_sq_meter=data.get("cost_per_sq_meter"),
        custom_attributes=data.get("custom_attributes", {})
    )

    try:
        new_material.save()
        return jsonify({
            "message": "Material created successfully!",
            "material_id": new_material.id
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route: Modify an individual material
@in_house_printing_bp.route("/update_material/<int:material_id>", methods=["PUT"])
def modify_material(material_id):
    data = request.get_json() or {}

    # Fetch the existing material by ID
    material = Material.query.get(material_id)
    if not material:
        return jsonify({"error": "Material not found."}), 404

    # Update fields if provided
    if "name" in data:
        material.name = data["name"]
    if "type" in data:
        material.type = data["type"]
    if "stock_level" in data:
        # Add to existing stock level or set directly?
        # If we want to replace the stock_level:
        # material.stock_level = data["stock_level"]
        # If we want to add to the existing stock level:
        material.stock_level += data["stock_level"]
    if "min_threshold" in data:
        material.min_threshold = data["min_threshold"]
    if "cost_per_sq_meter" in data:
        material.cost_per_sq_meter = data["cost_per_sq_meter"]
    if "custom_attributes" in data:
        material.custom_attributes = data["custom_attributes"]

    try:
        material.save()
        return jsonify({
            "message": "Material updated successfully!",
            "new_stock_level": material.stock_level
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route: Delete an individual material
@in_house_printing_bp.route("/delete_material/<int:material_id>", methods=["DELETE"])
def delete_material(material_id):
    material = Material.query.get(material_id)
    if not material:
        return jsonify({"error": "Material not found."}), 404

    try:
        material.delete()
        return jsonify({"message": "Material deleted successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route: Get all low-stock materials
@in_house_printing_bp.route("/materials/low-stock", methods=["GET"])
def get_low_stock_materials():
    low_stock_materials = MaterialService.check_stock_levels()
    return jsonify([material.serialize() for material in low_stock_materials]), 200


# Route: Log machine usage and material consumption for a job
@in_house_printing_bp.route("/jobs/<int:job_id>/machine-usage", methods=["POST"])
def log_machine_usage(job_id):
    data = request.json
    job = Job.query.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    start_meter = data.get("start_meter")
    end_meter = data.get("end_meter")
    material_id = data.get("material_id")

    # Validate material
    material = Material.query.get(material_id)
    if not material:
        return jsonify({"error": "Material not found"}), 404

    # Calculate material usage
    usage_amount = MachineUsageService.calculate_material_usage(start_meter, end_meter)

    # Update material stock level
    MaterialService.deduct_material_usage(material_id, usage_amount)

    # Log machine usage
    machine_reading = MachineReading(
        job_id=job_id,
        start_meter=start_meter,
        end_meter=end_meter,
        material_id=material_id,
        material_usage=usage_amount,
    )
    machine_reading.save()

    return jsonify({
        "message": "Machine usage logged successfully!",
        "material_usage": usage_amount,
        "job_id": job.id,
        "material": material.name
    }), 201


@in_house_printing_bp.route("/jobs/<int:job_id>/payment", methods=["POST"])
def update_payment(job_id):
    data = request.json
    payment_amount = data.get("amount")

    job = Job.query.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    try:
        job.update_payment(payment_amount)
        job.save()
        return jsonify({
            "message": "Payment updated successfully!",
            "job_id": job.id,
            "payment_status": job.payment_status,
            "amount_paid": job.amount_paid,
            "outstanding_amount": job.calculate_outstanding_amount()
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@in_house_printing_bp.route("/clients/<int:client_id>/outstanding-payments", methods=["GET"])
def get_outstanding_payments(client_id):
    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Client not found"}), 404

    outstanding_jobs = [
        {
            "job_id": job.id,
            "description": job.description,
            "total_amount": job.total_amount,
            "amount_paid": job.amount_paid,
            "outstanding_amount": job.calculate_outstanding_amount()
        }
        for job in client.jobs if job.payment_status != 'Paid'
    ]

    return jsonify({"client": client.name, "outstanding_jobs": outstanding_jobs}), 200


@in_house_printing_bp.route("/job/payment_statuses", methods=["GET"])
def get_payment_statuses():
    """
    Return the available payment status options for a job.
    This can be used by the frontend to populate dropdowns or selection controls.
    """
    # Since we know the defined Enum values in the model:
    statuses = ["Paid", "Partially Paid", "Unpaid"]
    return jsonify({"payment_statuses": statuses}), 200
