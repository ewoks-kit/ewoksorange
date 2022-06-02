from ewokscore import missing_data


# Native Orange widgets use `None` as MISSING_DATA
INVALIDATION_DATA = None


def is_invalid_data(value):
    """Invalid means either missing data or invalidation value"""
    return value is INVALIDATION_DATA or missing_data.is_missing_data(value)


def as_missing(value):
    """Convert INVALIDATION_DATA to MISSING_DATA"""
    if is_invalid_data(value):
        return missing_data.MISSING_DATA
    return value


def as_invalidation(value):
    """Convert MISSING_DATA to INVALIDATION_DATA"""
    if is_invalid_data(value):
        return INVALIDATION_DATA
    return value
