from marshmallow import Schema, fields, ValidationError, validate


class TimeframeSchema(Schema):
    start = fields.Date(required=False)
    end = fields.Date(required=False)


class ExpenseSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    cost = fields.Float(required=True, validate=validate.Range(min=0))
    shared = fields.Boolean(required=False)
    job_ids = fields.List(fields.Integer(), required=False)


class JobCreateSchema(Schema):
    client_id = fields.Integer(required=True, validate=validate.Range(min=1))
    description = fields.String(required=True, validate=validate.Length(min=1, max=500))
    material_id = fields.Integer(validate=validate.Range(min=1))
    material_usage_meters = fields.Float(validate=validate.Range(min=0))
    timeframe = fields.Nested(TimeframeSchema)
    progress_status = fields.String(
        validate=validate.OneOf(["pending", "in_progress", "completed"]),
        missing="pending"
    )
    pricing_input = fields.Float(validate=validate.Range(min=0), missing=0.0)
    expenses = fields.List(fields.Nested(ExpenseSchema), missing=[])


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
