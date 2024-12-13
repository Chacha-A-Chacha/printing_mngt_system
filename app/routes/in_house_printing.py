# routes/in_house_printing.py

from flask import request, jsonify
from . import in_house_printing_bp
from ..models.in_house_printing import Material, Job, MachineReading
from ..models.client import Client
from ..services.job_service import MaterialService, MachineUsageService


# Route: List all materials
@in_house_printing_bp.route("/materials", methods=["GET"])
def list_materials():
    materials = Material.query.all()
    return jsonify([material.serialize() for material in materials]), 200


# Route: Modify an individual material
@in_house_printing_bp.route("/materials/<int:material_id>", methods=["PUT"])
def modify_material(material_id):
    data = request.json
    material = Material.query.get(material_id)

    if not material:
        return jsonify({"error": "Material not found"}), 404

    # Update material attributes if provided
    if "name" in data:
        material.name = data["name"]
    if "type" in data:
        material.type = data["type"]
    if "stock_level" in data:
        material.stock_level = data["stock_level"]
    if "min_threshold" in data:
        material.min_threshold = data["min_threshold"]
    if "cost_per_sq_meter" in data:
        material.cost_per_sq_meter = data["cost_per_sq_meter"]
    if "custom_attributes" in data:
        material.custom_attributes = data["custom_attributes"]

    try:
        material.save()
        return jsonify({"message": "Material updated successfully!", "material": material.serialize()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route: Create a new material
@in_house_printing_bp.route("/materials", methods=["POST"])
def create_or_update_material():
    data = request.json
    material = Material.query.filter_by(name=data.get("name"), type=data.get("type")).first()

    if material:
        # Update existing material's stock level and optional fields
        material.stock_level += data.get("stock_level", 0)
        if "cost_per_sq_meter" in data:
            material.cost_per_sq_meter = data["cost_per_sq_meter"]
        if "custom_attributes" in data:
            material.custom_attributes = data["custom_attributes"]

        try:
            material.save()  # Persist changes
            return jsonify({"message": "Material updated successfully!", "new_stock_level": material.stock_level}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        # Create a new material
        try:
            material = Material(**data)
            material.save()  # Persist the new material
            return jsonify({"message": "Material created successfully!", "material_id": material.id}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500


# Route: Get all low-stock materials
@in_house_printing_bp.route("/materials/low-stock", methods=["GET"])
def get_low_stock_materials():
    low_stock_materials = MaterialService.check_stock_levels()
    return jsonify([material.serialize() for material in low_stock_materials]), 200


# Route: Create a new job linked to a client
@in_house_printing_bp.route("/jobs", methods=["POST"])
def create_job():
    data = request.json
    client_id = data.get("client_id")
    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Client not found"}), 404

    job = Job(client_id=client_id, description=data.get("description"))
    job.save()
    return jsonify({"message": "Job created successfully!", "job_id": job.id}), 201


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
