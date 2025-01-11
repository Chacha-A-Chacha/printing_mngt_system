from marshmallow import Schema, fields, validate, validates, ValidationError, pre_load
import re

from app import logger


class SupplierSchema(Schema):
    """
    Schema for Supplier model serialization/deserialization.
    Handles phone number validation and formatting.
    """
    id = fields.Int(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    phone_number = fields.String(
        required=True,
        validate=validate.Length(equal=12),
        description="Phone number in format 254XXXXXXXXX"
    )
    contact_info = fields.Dict(keys=fields.Str(), values=fields.Raw(), missing={})
    tax_id = fields.String(validate=validate.Length(max=50), allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @pre_load
    def clean_phone_number(self, data, **kwargs):
        """Clean phone number before validation"""
        if 'phone_number' in data:
            # Remove spaces and special characters
            phone = re.sub(r'[^0-9]', '', data['phone_number'])

            # Handle +254 prefix
            if phone.startswith('254'):
                data['phone_number'] = phone
            elif phone.startswith('0'):
                data['phone_number'] = '254' + phone[1:]
            elif phone.startswith('7') or phone.startswith('1'):
                data['phone_number'] = '254' + phone
            else:
                raise ValidationError("Invalid phone number format")

        return data

    @validates('phone_number')
    def validate_phone_number(self, value):
        """Validate phone number format"""
        if not value.startswith('254'):
            raise ValidationError("Phone number must start with 254")

        if not len(value) == 12:
            raise ValidationError("Phone number must be 12 digits")

        if not value.isdigit():
            raise ValidationError("Phone number must contain only digits")
