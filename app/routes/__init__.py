from flask import Blueprint

# Authentication routes
auth_bp = Blueprint('auth', __name__)

# Material handling routes
materials_bp = Blueprint('materials', __name__)

# Job handling routes
jobs_bp = Blueprint('jobs', __name__)

# In-House Printing routes
in_house_printing_bp = Blueprint('in_house_printing', __name__)

# Outsourced Production routes
outsourced_production_bp = Blueprint('outsourced_production', __name__)

# Client management routes
client_bp = Blueprint('client', __name__)

# Supplier management routes
supplier_bp = Blueprint('supplier', __name__)

# Machine logging routes
machine_logs_bp = Blueprint('machine', __name__)

# Reporting routes
reporting_bp = Blueprint('reporting', __name__)

# Import route handlers to register routes
from . import (
    auth,
    materials,
    jobs,
    in_house_printing,
    client,
    supplier,
    machine_logs,
    reporting
)
