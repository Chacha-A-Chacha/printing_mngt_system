#!usr/bin/python3
#
from datetime import datetime
from flask import request, jsonify

from . import materials_bp
from ..schemas.materials_schemas import MaterialCreateSchema, MaterialUsageCreateSchema, MaterialRestockSchema, \
    StockAdjustmentSchema
from ..services.material_service import MaterialService


@materials_bp.route("/materials", methods=["POST"])
def create_material():
    """
        Create a new material
        ---
        tags:
          - Materials
        requestBody:
          content:
            application/json:
              schema: MaterialCreateSchema
        responses:
          201:
            description: Material created successfully
          400:
            description: Validation error
          500:
            description: Internal server error
        """
    schema = MaterialCreateSchema()

    try:
        data = schema.load(request.get_json())
        material = MaterialService.create_material(data)
        return jsonify({
            "message": "Material created successfully",
            "material": material.serialize()
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@materials_bp.route("/materials", methods=["GET"])
def list_materials():
    filters = request.args.to_dict()
    materials = MaterialService.get_materials(filters)
    return jsonify([material.serialize() for material in materials]), 200


@materials_bp.route("/materials/usage", methods=["POST"])
def record_usage():
    """
        Record material usage for a job
        ---
        tags:
          - Materials
        requestBody:
          content:
            application/json:
              schema: MaterialUsageCreateSchema
        responses:
          201:
            description: Material usage recorded successfully
          400:
            description: Validation error or insufficient stock
          500:
            description: Internal server error
    """
    schema = MaterialUsageCreateSchema()

    try:
        data = schema.load(request.get_json())
        usage = MaterialService.record_material_usage(data)
        return jsonify({
            "message": "Material usage recorded successfully",
            "usage": {
                "id": usage.id,
                "material_id": usage.material_id,
                "job_id": usage.job_id,
                "quantity_used": usage.quantity_used,
                "wastage": usage.wastage,
                "remaining_stock": usage.material.stock_level,
                "user_id": usage.user_id,
                "created_at": usage.created_at.isoformat()
            }
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@materials_bp.route("/materials/restock", methods=["POST"])
def restock_material():
    """
        Record material restock from supplier
        ---
        tags:
          - Materials
        requestBody:
          content:
            application/json:
              schema: MaterialRestockSchema
        responses:
          201:
            description: Material restocked successfully
          400:
            description: Validation error
          404:
            description: Material not found
          500:
            description: Internal server error
    """
    schema = MaterialRestockSchema()
    try:
        data = schema.load(request.get_json())
        transaction = MaterialService.restock_material(data)
        return jsonify({
            "message": "Material restocked successfully",
            "transaction": {
                "id": transaction.id,
                "material_id": transaction.material_id,
                "quantity": transaction.quantity,
                "previous_stock": transaction.previous_stock,
                "new_stock_level": transaction.new_stock,
                "reference_number": transaction.reference_number,
                "cost_per_unit": transaction.cost_per_unit,
                "supplier_id": transaction.supplier_id,
                "user_id": transaction.user_id,
                "created_at": transaction.created_at.isoformat(),
                "notes": transaction.notes
            }
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@materials_bp.route("/materials/adjust-stock", methods=["POST"])
def adjust_stock():
    """
        Adjust material stock level (for corrections/inventory count)
        ---
        tags:
          - Materials
        requestBody:
          content:
            application/json:
              schema: StockAdjustmentSchema
        responses:
          201:
            description: Stock adjusted successfully
          400:
            description: Validation error
          404:
            description: Material not found
          500:
            description: Internal server error
    """
    schema = StockAdjustmentSchema()
    try:
        data = schema.load(request.get_json())
        transaction = MaterialService.adjust_stock(data)
        return jsonify({
            "message": "Stock adjusted successfully",
            "transaction": {
                "id": transaction.id,
                "material_id": transaction.material_id,
                "adjustment": transaction.quantity,  # Difference between old and new
                "previous_stock": transaction.previous_stock,
                "new_stock_level": transaction.new_stock,
                "adjustment_reason": transaction.adjustment_reason,
                "reference_number": transaction.reference_number,
                "notes": transaction.notes,
                "user_id": transaction.user_id,
                "created_at": transaction.created_at.isoformat()
            }
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@materials_bp.route("/materials/search", methods=["GET"])
def search_materials():
    search_term = request.args.get('q', '')
    category = request.args.get('category')
    supplier_id = request.args.get('supplier_id', type=int)

    materials = MaterialService.search_materials(
        search_term=search_term,
        category=category,
        supplier_id=supplier_id
    )

    return jsonify([material.serialize() for material in materials]), 200


@materials_bp.route("/materials/<material_code>", methods=["GET"])
def get_material_by_code(material_code):
    material = MaterialService.get_material_by_code(material_code)

    if not material:
        return jsonify({"error": "Material not found"}), 404

    return jsonify(material.serialize()), 200


@materials_bp.route("/materials/transactions/<int:material_id>", methods=["GET"])
def get_material_transactions(material_id):
    transaction_type = request.args.get('type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date:
        start_date = datetime.fromisoformat(start_date)
    if end_date:
        end_date = datetime.fromisoformat(end_date)

    transactions = MaterialService.get_stock_transactions(
        material_id=material_id,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date
    )

    return jsonify([tx.serialize() for tx in transactions]), 200
