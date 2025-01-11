# routes/supplier.py
from flask import jsonify, request
from marshmallow import ValidationError
from . import supplier_bp
from ..services.supplier_service import SupplierService
from ..schemas.supplier_schema import SupplierSchema

from app import logger


@supplier_bp.route("/suppliers", methods=["POST"])
def create_supplier():
    """
    Create a new supplier
    ---
    tags:
      - Suppliers
    requestBody:
      content:
        application/json:
          schema: SupplierSchema
    responses:
      201:
        description: Supplier created successfully
      400:
        description: Validation error
      500:
        description: Internal server error
    """
    schema = SupplierSchema()
    try:
        data = schema.load(request.get_json())
        supplier = SupplierService.create_supplier(data)
        return jsonify({
            "message": "Supplier created successfully",
            "supplier": schema.dump(supplier)
        }), 201
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": e.messages}), 400
    except Exception as e:
        logger.error(f"Error creating supplier: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@supplier_bp.route("/suppliers", methods=["GET"])
def list_suppliers():
    """
    Get all suppliers
    ---
    tags:
      - Suppliers
    responses:
      200:
        description: List of suppliers
      500:
        description: Internal server error
    """
    try:
        suppliers = SupplierService.get_suppliers()
        schema = SupplierSchema(many=True)
        return jsonify(schema.dump(suppliers)), 200
    except Exception as e:
        logger.error(f"Error listing suppliers: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
