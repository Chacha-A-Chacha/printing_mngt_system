#!usr/bin/python3
from flask import request, jsonify

from . import materials_bp
from ..services.material_service import MaterialService


@materials_bp.route("/materials", methods=["POST"])
def create_material():
    data = request.get_json()

    try:
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
    data = request.get_json()

    try:
        usage = MaterialService.record_material_usage(data)
        return jsonify({
            "message": "Material usage recorded successfully",
            "usage": {
                "id": usage.id,
                "material_id": usage.material_id,
                "quantity_used": usage.quantity_used,
                "wastage": usage.wastage,
                "remaining_stock": usage.material.stock_level
            }
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@materials_bp.route("/materials/restock", methods=["POST"])
def restock_material():
    data = request.get_json()

    try:
        transaction = MaterialService.restock_material(data)
        return jsonify({
            "message": "Material restocked successfully",
            "transaction": {
                "id": transaction.id,
                "material_id": transaction.material_id,
                "quantity": transaction.quantity,
                "new_stock_level": transaction.new_stock,
                "reference_number": transaction.reference_number
            }
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@materials_bp.route("/materials/adjust-stock", methods=["POST"])
def adjust_stock():
    data = request.get_json()

    try:
        transaction = MaterialService.adjust_stock(data)
        return jsonify({
            "message": "Stock adjusted successfully",
            "transaction": {
                "id": transaction.id,
                "material_id": transaction.material_id,
                "adjustment": transaction.quantity,
                "new_stock_level": transaction.new_stock,
                "reference_number": transaction.reference_number
            }
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500