from marshmallow import Schema, fields, validates, ValidationError


class MachineCreateSchema(Schema):
    """Schema for creating a new machine"""
    name = fields.Str(required=True)
    model = fields.Str(required=True)
    serial_number = fields.Str(required=True)
    status = fields.Str(missing='active')


class MachineSchema(Schema):
    """Schema for machine responses"""
    id = fields.Int()
    name = fields.Str()
    model = fields.Str()
    serial_number = fields.Str()
    status = fields.Str()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class MachineReadingCreateSchema(Schema):
    """Schema for creating a new machine reading"""
    job_id = fields.Int(required=True)
    machine_id = fields.Int(required=True)
    start_meter = fields.Float(required=True)
    end_meter = fields.Float(required=True)
    operator_id = fields.Int(allow_none=True)

    @validates('end_meter')
    def validate_end_meter(self, value):
        if 'start_meter' in self.data and value < self.data['start_meter']:
            raise ValidationError("End meter reading must be greater than start meter reading")


class MachineReadingSchema(Schema):
    """Schema for machine reading responses"""
    id = fields.Int()
    job_id = fields.Int()
    machine_id = fields.Int()
    start_meter = fields.Float()
    end_meter = fields.Float()
    operator_id = fields.Int(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
