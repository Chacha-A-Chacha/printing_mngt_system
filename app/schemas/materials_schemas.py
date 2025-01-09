# schemas/material.py
from marshmallow import Schema, fields, validate, ValidationError


class MaterialCreateSchema(Schema):
    """
    Primary schema for creating a new material.
    - Handles basic material properties
    - Includes stock management fields
    - Optional custom attributes
    """
    # Basic material info
    material_code = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50),
        description="Unique identifier for the material"
    )
    name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100),
        description="Material name"
    )
    category = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50),
        description="Primary category of material"
    )
    type = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50),
        description="Specific type within category"
    )

    # Stock management
    unit_of_measure = fields.String(
        required=True,
        validate=validate.Length(min=1, max=20),
        description="Unit of measurement (e.g., meters, rolls)"
    )
    stock_level = fields.Float(
        validate=validate.Range(min=0),
        missing=0.0,
        description="Current stock level"
    )
    min_threshold = fields.Float(
        required=True,
        validate=validate.Range(min=0),
        description="Minimum stock level before reorder"
    )
    reorder_quantity = fields.Float(
        required=True,
        validate=validate.Range(min=0),
        description="Quantity to reorder when below threshold"
    )

    # Cost information
    cost_per_unit = fields.Float(
        required=True,
        validate=validate.Range(min=0),
        description="Cost per unit of measurement"
    )

    # Relationships
    supplier_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        description="ID of the supplier"
    )

    # Optional fields
    specifications = fields.Dict(keys=fields.Str(), values=fields.Raw(), missing={})
    custom_attributes = fields.Dict(keys=fields.Str(), values=fields.Raw(), missing={})


class MaterialUsageCreateSchema(Schema):
    """
    Schema for recording material usage in a job.
    - Tracks material consumption
    - Records wastage
    - Links usage to specific job and user
    """
    # Required fields
    material_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        description="ID of the material being used"
    )
    job_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        description="ID of the job this usage is for"
    )
    quantity_used = fields.Float(
        required=True,
        validate=validate.Range(min=0.1),
        description="Amount of material used in the job"
    )
    user_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        description="ID of user recording the usage"
    )

    # Optional fields
    wastage = fields.Float(
        validate=validate.Range(min=0),
        missing=0.0,
        description="Amount of material wasted during job"
    )
    notes = fields.String(
        validate=validate.Length(max=255),
        missing=None,
        description="Additional notes about usage"
    )


class MaterialRestockSchema(Schema):
    """
    Schema for recording material restock/inventory addition.
    - Tracks stock additions from suppliers
    - Records purchase/delivery references
    - Maintains audit trail with user tracking
    """
    material_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        description="ID of the material being restocked"
    )
    quantity = fields.Float(
        required=True,
        validate=validate.Range(min=0.1),
        description="Quantity being added to stock"
    )
    user_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        description="ID of user recording the restock"
    )
    reference_number = fields.String(
        required=True,
        validate=validate.Length(min=1, max=50),
        description="Purchase order or delivery reference"
    )
    cost_per_unit = fields.Float(
        validate=validate.Range(min=0),
        missing=None,
        description="Cost per unit for this specific restock"
    )
    supplier_id = fields.Integer(
        validate=validate.Range(min=1),
        missing=None,
        description="ID of supplier for this delivery"
    )
    notes = fields.String(
        validate=validate.Length(max=255),
        missing=None,
        description="Additional notes about restock"
    )


class StockAdjustmentSchema(Schema):
    """
    Schema for material stock adjustments.
    - Handles inventory corrections
    - Records reason for adjustment
    - Maintains audit trail
    """
    material_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        description="ID of the material being adjusted"
    )
    new_stock_level = fields.Float(
        required=True,
        validate=validate.Range(min=0),
        description="New total stock level after adjustment"
    )
    user_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        description="ID of user performing adjustment"
    )
    adjustment_reason = fields.String(
        required=True,
        validate=validate.OneOf([
            "INVENTORY_COUNT",
            "DAMAGE",
            "QUALITY_ISSUE",
            "SYSTEM_CORRECTION",
            "OTHER"
        ]),
        description="Reason for stock adjustment"
    )
    reference_number = fields.String(
        validate=validate.Length(max=50),
        missing=None,
        description="Reference number for adjustment"
    )
    notes = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255),
        description="Detailed explanation for adjustment"
    )