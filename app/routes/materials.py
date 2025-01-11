#!usr/bin/python3
#
from datetime import datetime
from flask import request, jsonify, send_file
from marshmallow import ValidationError
from .. import logger
from . import materials_bp
from ..schemas.materials_schemas import MaterialCreateSchema, MaterialUsageCreateSchema, MaterialRestockSchema, \
    StockAdjustmentSchema, StockReportRequestSchema, MaterialUsageReportRequestSchema
from ..services.material_service import MaterialService, ReportingService


@materials_bp.route("/create", methods=["POST"])
def create_material():
    logger.debug(request.json)
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
            
            // POST /materials/create
            // Request
            {
                "material_code": "VNL-001",
                "name": "Premium Vinyl",
                "category": "Vinyl",
                "type": "Adhesive",
                "unit_of_measure": "meters",
                "min_threshold": 100.0,
                "reorder_quantity": 500.0,
                "cost_per_unit": 15.5,
                "supplier": {
                    "name": "Premium Vinyl Supplier",
                    "phone_number": "254712345678",
                    "contact_info": {
                        "email": "contact@premiumvinyl.com"
                    }
                },
                "specifications": {
                    "width": 1.52,
                    "thickness": 0.08
                }
            }
            
            // Response 201
            {
                "message": "Material created successfully",
                "material": {
                    "material_code": "VNL-001",
                    "name": "Premium Vinyl",
                    "category": "Vinyl",
                    "type": "Adhesive",
                    "unit_of_measure": "meters",
                    "stock_level": 0.0,
                    "min_threshold": 100.0,
                    "reorder_quantity": 500.0,
                    "cost_per_unit": 15.5,
                    "specifications": {
                        "width": 1.52,
                        "thickness": 0.08
                    },
                    "supplier": {
                        "name": "Premium Vinyl Supplier",
                        "phone_number": "254712345678",
                        "contact_info": {
                            "email": "contact@premiumvinyl.com"
                        }
                    },
                    "created_at": "2025-01-11T15:30:00",
                    "updated_at": "2025-01-11T15:30:00"
                }
            }
        """
    schema = MaterialCreateSchema()

    try:
        data = schema.load(request.get_json())
        material = MaterialService.create_material(data)
        logger.info(f"Created new material: {material}")
        return jsonify({
            "message": "Material created successfully",
            "material": material.serialize()
        }), 201
    except ValueError as e:
        logger.error(e)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(e)
        return jsonify({"error": "Internal server error"}), 500


@materials_bp.route("/list", methods=["GET"])
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


@materials_bp.route("/restock", methods=["POST"])
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


@materials_bp.route("/adjust-stock", methods=["POST"])
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


@materials_bp.route("/search", methods=["GET"])
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


@materials_bp.route("/code/<material_code>", methods=["GET"])
def get_material_by_code(material_code):
    material = MaterialService.get_material_by_code(material_code)

    if not material:
        return jsonify({"error": "Material not found"}), 404

    return jsonify(material.serialize()), 200


@materials_bp.route("/transactions/<int:material_id>", methods=["GET"])
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


@materials_bp.route("/reports/stock", methods=["GET"])
def get_stock_report():
    """
    Get stock report data or download report file
    ---
    tags:
      - Reports
    parameters:
      - in: query
        schema: StockReportRequestSchema
    responses:
      200:
        description: Report data or file
        content:
          application/json:
            schema:
              type: object
              properties:
                data: array
                metadata: object
                charts: object
          application/pdf:
            schema:
              type: string
              format: binary
          application/vnd.ms-excel:
            schema:
              type: string
              format: binary
    """
    try:
        schema = StockReportRequestSchema()
        params = schema.load(request.args)

        # Get the base report data
        report_data = ReportingService.get_stock_report_data(params)

        if params['view_type'] == 'DISPLAY':
            # Return JSON for frontend display
            return jsonify({
                "data": report_data['items'],
                "metadata": {
                    "total_items": len(report_data['items']),
                    "total_value": report_data['total_value'],
                    "last_updated": report_data['last_updated'],
                    "filters_applied": params
                },
                "charts": {
                    "stock_levels": report_data['chart_data']['stock_levels'],
                    "category_distribution": report_data['chart_data']['categories'],
                    "value_distribution": report_data['chart_data']['values']
                }
            }), 200

        else:  # File download
            file_data = ReportingService.generate_report_file(
                report_data,
                params['view_type']
            )

            filename = f"stock_report_{datetime.now().strftime('%Y%m%d')}"

            if params['view_type'] == 'PDF':
                mimetype = 'application/pdf'
                filename += '.pdf'
            elif params['view_type'] == 'CSV':
                mimetype = 'text/csv'
                filename += '.csv'
            else:  # EXCEL
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                filename += '.xlsx'

            return send_file(
                file_data,
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )

    except ValidationError as e:
        return jsonify({"error": e.messages}), 400.


@materials_bp.route("/reports/usage", methods=["GET"])
def get_usage_report():
    """
    Get material usage report data or download report file
    ---
    tags:
      - Reports
    parameters:
      - in: query
        schema: MaterialUsageReportRequestSchema
    responses:
      200:
        description: Report data or file
    """
    try:
        schema = MaterialUsageReportRequestSchema()
        params = schema.load(request.args)

        # Validate date range
        if params['end_date'] < params['start_date']:
            raise ValidationError("End date must be after start date")

        # Get the base report data
        report_data = ReportingService.get_usage_report_data(params)

        if params['view_type'] == 'DISPLAY':
            return jsonify({
                "data": report_data['items'],
                "metadata": {
                    "total_usage": report_data['total_usage'],
                    "total_wastage": report_data['total_wastage'],
                    "efficiency_rate": report_data['efficiency_rate'],
                    "date_range": {
                        "start": params['start_date'].isoformat(),
                        "end": params['end_date'].isoformat()
                    },
                    "filters_applied": params
                },
                "charts": {
                    "usage_over_time": report_data['chart_data']['timeline'],
                    "usage_by_material": report_data['chart_data']['materials'],
                    "wastage_analysis": report_data['chart_data']['wastage']
                },
                "summary": {
                    "most_used_material": report_data['summary']['most_used'],
                    "highest_wastage": report_data['summary']['highest_wastage'],
                    "busiest_period": report_data['summary']['peak_usage']
                }
            }), 200

        else:  # File download
            file_data = ReportingService.generate_report_file(
                report_data,
                params['view_type']
            )

            filename = f"material_usage_{datetime.now().strftime('%Y%m%d')}"

            if params['view_type'] == 'PDF':
                mimetype = 'application/pdf'
                filename += '.pdf'
            elif params['view_type'] == 'CSV':
                mimetype = 'text/csv'
                filename += '.csv'
            else:  # EXCEL
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                filename += '.xlsx'

            return send_file(
                file_data,
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )

    except ValidationError as e:
        return jsonify({"error": e.messages}), 400
