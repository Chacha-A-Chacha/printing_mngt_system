from flask import jsonify

from . import reporting_bp
from .. import db
from ..models.in_house_printing import Material, MachineReading, Client, Job


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

