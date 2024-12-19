def _determine_update_type(data):
    """
    A simple heuristic to determine the update type.
    For example:
    - If 'progress_status' in data -> progress update
    - If 'material_id' and 'additional_usage_meters' in data -> material usage update
    - If 'expenses' in data -> expenses update
    - If 'start_date' or 'end_date' in data -> timeframe update
    """
    if 'progress_status' in data:
        return 'progress'
    elif 'material_id' in data and 'additional_usage_meters' in data:
        return 'material_usage'
    elif 'expenses' in data:
        return 'expenses'
    elif 'start_date' in data or 'end_date' in data:
        return 'timeframe'
    return None
