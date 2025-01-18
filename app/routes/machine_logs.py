from datetime import datetime
from flask import request, jsonify

from . import machine_logs_bp
from .. import logger
from ..models.machine import Machine, MachineReading
from ..schemas.machine_schema import MachineCreateSchema, MachineReadingCreateSchema
from ..services.machine_service import MachineService, MachineReadingService


@machine_logs_bp.route("/list", methods=["GET"])
def list_machines():
    """
    Get a list of all machines
    ---
    tags:
      - Machines
    responses:
      200:
        description: List of machines retrieved successfully
      500:
        description: Internal server error

        // GET /machines/list
        // Response 200
        {
            "machines": [
                {
                    "id": 1,
                    "name": "Roland XR-640",
                    "model": "XR-640",
                    "serial_number": "RL12345678",
                    "status": "active",
                    "created_at": "2025-01-16T10:30:00",
                    "updated_at": "2025-01-16T10:30:00"
                }
            ]
        }
    """
    try:
        machines = Machine.query.all()
        return jsonify({
            "machines": [machine.serialize() for machine in machines]
        }), 200
    except Exception as e:
        logger.error(e)
        return jsonify({"error": "Internal server error"}), 500


@machine_logs_bp.route("/create", methods=["POST"])
def create_machine():
    logger.debug(request.json)
    """
    Create a new machine
    ---
    tags:
      - Machines
    requestBody:
      content:
        application/json:
          schema: MachineCreateSchema
    responses:
      201:
        description: Machine created successfully
      400:
        description: Validation error
      500:
        description: Internal server error
    """
    schema = MachineCreateSchema()

    try:
        data = schema.load(request.get_json())
        machine = MachineService.create_machine(data)
        logger.info(f"Created new machine: {machine}")
        return jsonify({
            "message": "Machine created successfully",
            "machine": machine.serialize()
        }), 201
    except ValueError as e:
        logger.error(e)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(e)
        return jsonify({"error": "Internal server error"}), 500


@machine_logs_bp.route("/readings/create", methods=["POST"])
def create_machine_reading():
    logger.debug(request.json)
    """
    Create a new machine reading
    ---
    tags:
      - Machine Readings
    requestBody:
      content:
        application/json:
          schema: MachineReadingCreateSchema
    responses:
      201:
        description: Machine reading created successfully
      400:
        description: Validation error
      500:
        description: Internal server error
    """
    schema = MachineReadingCreateSchema()

    try:
        data = schema.load(request.get_json())
        reading = MachineReadingService.create_reading(data)
        logger.info(f"Created new machine reading: {reading}")
        return jsonify({
            "message": "Machine reading created successfully",
            "reading": reading.serialize()
        }), 201
    except ValueError as e:
        logger.error(e)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(e)
        return jsonify({"error": "Internal server error"}), 500


@machine_logs_bp.route("/readings/job/<int:job_id>", methods=["GET"])
def get_job_readings(job_id):
    """
    Get all machine readings for a specific job
    ---
    tags:
      - Machine Readings
    parameters:
      - name: job_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: List of machine readings for the job
      404:
        description: Job not found
      500:
        description: Internal server error
    """
    try:
        readings = MachineReadingService.get_job_readings(job_id)
        return jsonify({
            "readings": [reading.serialize() for reading in readings]
        }), 200
    except ValueError as e:
        logger.error(e)
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(e)
        return jsonify({"error": "Internal server error"}), 500


@machine_logs_bp.route("/readings/machine/<int:machine_id>", methods=["GET"])
def get_machine_readings(machine_id):
    """
    Get machine readings for a specific machine
    ---
    tags:
      - Machine Readings
    parameters:
      - name: machine_id
        in: path
        required: true
        schema:
          type: integer
      - name: start_date
        in: query
        required: false
        schema:
          type: string
          format: date
      - name: end_date
        in: query
        required: false
        schema:
          type: string
          format: date
    responses:
      200:
        description: List of machine readings
      404:
        description: Machine not found
      500:
        description: Internal server error
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        readings = MachineReadingService.get_machine_readings(machine_id, start_date, end_date)
        total_usage = MachineReadingService.get_machine_total_usage(machine_id, start_date, end_date)

        return jsonify({
            "readings": [reading.serialize() for reading in readings],
            "total_usage": total_usage
        }), 200
    except ValueError as e:
        logger.error(e)
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(e)
        return jsonify({"error": "Internal server error"}), 500


@machine_logs_bp.route("/readings/list", methods=["GET"])
def list_machine_readings():
    """
    Get paginated list of all machine readings
    ---
    tags:
      - Machine Readings
    parameters:
      - name: page
        in: query
        required: false
        schema:
          type: integer
          default: 1
      - name: per_page
        in: query
        required: false
        schema:
          type: integer
          default: 10
    responses:
      200:
        description: List of machine readings retrieved successfully
      500:
        description: Internal server error
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Get paginated readings with machines joined
        pagination = MachineReading.query\
            .join(Machine)\
            .order_by(MachineReading.created_at.desc())\
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )

        readings = pagination.items

        return jsonify({
            "readings": [{
                "id": reading.id,
                "machine_id": reading.machine_id,
                "machine_name": f"{reading.machine.name} - {reading.machine.model}",
                "job_id": reading.job_id,
                "start_meter": reading.start_meter,
                "end_meter": reading.end_meter,
                "operator_id": reading.operator_id,
                "operator_name": reading.operator.name if reading.operator else None,
                "created_at": reading.created_at.isoformat(),
            } for reading in readings],
            "pagination": {
                "current_page": page,
                "total_pages": pagination.pages,
                "total_items": pagination.total,
                "items_per_page": per_page
            }
        }), 200
    except Exception as e:
        logger.error(e)
        return jsonify({"error": "Internal server error"}), 500


@machine_logs_bp.route("/readings/list", methods=["GET"])
def list_readings():
    """
    Get paginated list of all machine readings
    ---
    tags:
      - Machine Readings
    parameters:
      - name: page
        in: query
        required: false
        schema:
          type: integer
          default: 1
      - name: per_page
        in: query
        required: false
        schema:
          type: integer
          default: 10
    responses:
      200:
        description: List of machine readings retrieved successfully
      500:
        description: Internal server error
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Get paginated readings with machines joined
        pagination = MachineReading.query\
            .join(Machine)\
            .order_by(MachineReading.created_at.desc())\
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )

        readings = pagination.items

        return jsonify({
            "readings": [{
                **reading.serialize(),
                "machine_name": f"{reading.machine.name} - {reading.machine.model}",
                "operator_name": reading.operator.name if reading.operator else None
            } for reading in readings],
            "pagination": {
                "current_page": page,
                "total_pages": pagination.pages,
                "total_items": pagination.total,
                "items_per_page": per_page
            }
        }), 200
    except Exception as e:
        logger.error(f"Error listing machine readings: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
