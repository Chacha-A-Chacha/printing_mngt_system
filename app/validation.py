from app.schemas.job_schemas import JobCreateSchema


def validate_job_input(data):
    schema = JobCreateSchema()
    try:
        validated_data = schema.load(data)
        return validated_data, None
    except ValidationError as err:
        return None, err.messages


def validate_material_input(data):
    schema = MaterialCreateSchema()
    pass
