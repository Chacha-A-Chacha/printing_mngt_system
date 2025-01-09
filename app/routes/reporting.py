from flask import jsonify

from . import reporting_bp
from .. import db
from ..models.materials import Material
from ..models.client import Client
from ..models.job import Job
from ..models.machine import MachineReading


@reporting_bp.route("/reports/material-usage", methods=["GET"])
def get_material_usage_report():
    """
    Material Usage Report: Query material usage, job details, and client information.
    :return:
    """

    results = db.session.query(
        MachineReading.material_id,
        Material.name.label("material_name"),
        MachineReading.material_usage,
        Job.id.label("job_id"),
        Client.name.label("client_name")
    ).join(Material, MachineReading.material_id == Material.id) \
        .join(Job, MachineReading.job_id == Job.id) \
        .join(Client, Job.client_id == Client.id) \
        .all()
    return jsonify(results)


@reporting_bp.route("/reports/jobs", methods=["GET"])
def get_job_report():
    """
    Jobs Linked to Materials and Clients: Query all jobs, their clients, and associated materials.
    :return:
    """

    results = db.session.query(
        Job.id,
        Job.description,
        Client.name.label("client_name"),
        Material.name.label("material_name"),
        MachineReading.start_meter,
        MachineReading.end_meter,
        MachineReading.material_usage
    ).join(Client, Job.client_id == Client.id) \
        .join(MachineReading, MachineReading.job_id == Job.id) \
        .join(Material, MachineReading.material_id == Material.id) \
        .all()
    return jsonify(results)


@reporting_bp.route("/jobs/<int:job_id>/usage", methods=["GET"])
def get_job_usage(job_id):
    """

    :param job_id:
    :return:
    """

    usage_details = db.session.query(
        MachineReading.start_meter,
        MachineReading.end_meter,
        MachineReading.material_usage,
        Material.name.label("material_name"),
        Client.name.label("client_name")
    ).join(Material, MachineReading.material_id == Material.id)\
     .join(Job, MachineReading.job_id == Job.id)\
     .join(Client, Job.client_id == Client.id)\
     .filter(Job.id == job_id)\
     .all()
    return jsonify(usage_details)


@reporting_bp.route("/reports/outstanding-payments", methods=["GET"])
def outstanding_payment_report():
    results = db.session.query(
        Client.name.label("client_name"),
        Job.id.label("job_id"),
        Job.description,
        Job.total_amount,
        Job.amount_paid,
        (Job.total_amount - Job.amount_paid).label("outstanding_amount")
    ).filter(Job.payment_status != 'Paid').join(Client, Client.id == Job.client_id).all()

    report = [{
        "client_name": r.client_name,
        "job_id": r.job_id,
        "description": r.description,
        "total_amount": r.total_amount,
        "amount_paid": r.amount_paid,
        "outstanding_amount": r.outstanding_amount
    } for r in results]

    return jsonify(report), 200
