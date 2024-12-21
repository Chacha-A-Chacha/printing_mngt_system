from marshmallow import Schema, fields, validate


class TimeframeSchema(Schema):
    """
    Represents optional timeframe data (start/end).
    This is embedded in some job schemas when a timeframe is relevant.
    """
    start = fields.Date(required=False)
    end = fields.Date(required=False)


class ExpenseSchema(Schema):
    """
    Represents an expense that may be directly associated with a job
    or shared among multiple jobs.
    """
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    cost = fields.Float(required=True, validate=validate.Range(min=0))
    shared = fields.Boolean(required=False, missing=False)
    job_ids = fields.List(fields.Integer(), required=False)


from marshmallow import Schema, fields, validate, ValidationError


class JobCreateSchema(Schema):
    """
    Primary schema for creating a new job.
    - Handles both in-house and outsourced jobs.
    - Client name and phone are used to find or create a client record.
    - job_type determines whether certain outsourced fields are relevant.
    - material_usage and expenses can be supplied if known at creation,
      or added later via partial update routes.
    """
    # Client fields
    client_name = fields.String(
        required=True,
        validate=validate.Length(min=1),
        description="Client’s full name."
    )
    client_phone_number = fields.String(
        required=True,
        validate=validate.Length(min=1),
        description="Client’s phone number (unique identifier)."
    )

    # Basic job info
    description = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500),
        description="Short description of the job."
    )
    job_type = fields.String(
        required=True,
        validate=validate.OneOf(["in_house", "outsourced"]),
        description="Specifies whether production is internal or outsourced."
    )

    # In-House optional fields (if job_type == 'in_house')
    material_id = fields.Integer(validate=validate.Range(min=1))
    material_usage_meters = fields.Float(validate=validate.Range(min=0))

    # Outsourced optional fields (if job_type == 'outsourced')
    vendor_name = fields.String(
        required=False,
        allow_none=True,
        description="Name of the external vendor."
    )
    vendor_cost_per_unit = fields.Float(
        required=False,
        allow_none=True,
        validate=validate.Range(min=0),
        description="Cost charged by vendor per piece/unit."
    )
    total_units = fields.Integer(
        required=False,
        allow_none=True,
        validate=validate.Range(min=0),
        description="Number of pieces/units for outsourced jobs."
    )
    pricing_per_unit = fields.Float(
        required=False,
        allow_none=True,
        validate=validate.Range(min=0),
        description="Price to client per unit for outsourced jobs."
    )

    # Timeframe and status
    timeframe = fields.Nested(TimeframeSchema, required=False)
    progress_status = fields.String(
        validate=validate.OneOf(["pending", "in_progress", "completed"]),
        missing="pending"
    )

    # Base pricing input if not using unit-based pricing
    pricing_input = fields.Float(validate=validate.Range(min=0), missing=0.0)

    # Optional expenses at creation time
    expenses = fields.List(fields.Nested(ExpenseSchema), missing=[])

    def validate_job_data(self, data):
        """
        (Optional) Additional logic to ensure correct usage of fields
        based on job_type. Could be called post-load to raise a ValidationError
        if in-house fields are supplied for an outsourced job, etc.
        """
        job_type = data.get('job_type')
        if job_type == 'in_house':
            # Possibly check if vendor_name or vendor_cost_per_unit is absent or None
            pass
        elif job_type == 'outsourced':
            # Possibly check if material_id/material_usage_meters are absent or None
            pass

    def load(self, data, **kwargs):
        loaded_data = super().load(data, **kwargs)
        self.validate_job_data(loaded_data)
        return loaded_data


class JobProgressUpdateSchema(Schema):
    progress_status = fields.String(
        required=True,
        validate=validate.OneOf([
            "pending",
            "in_progress",
            "on_hold",
            "completed",
            "cancelled"
        ])
    )
    notes = fields.String(allow_none=True, validate=validate.Length(max=1000))
    completed_at = fields.DateTime(allow_none=True)
    reason_for_status_change = fields.String(allow_none=True, validate=validate.Length(max=500))


class JobMaterialUpdateSchema(Schema):
    material_id = fields.Integer(required=True, validate=validate.Range(min=1))
    additional_usage_meters = fields.Float(required=True, validate=validate.Range(min=0.1))


class JobExpenseUpdateSchema(Schema):
    expenses = fields.List(fields.Nested({
        'name': fields.String(required=True, validate=validate.Length(min=1)),
        'cost': fields.Float(required=True, validate=validate.Range(min=0)),
        'date': fields.Date(allow_none=True),
        'category': fields.String(allow_none=True),
        'receipt_url': fields.URL(allow_none=True)
    }), required=True)


class JobTimeframeUpdateSchema(Schema):
    start_date = fields.Date(allow_none=True)
    end_date = fields.Date(allow_none=True)
    reason_for_change = fields.String(allow_none=True, validate=validate.Length(max=500))
