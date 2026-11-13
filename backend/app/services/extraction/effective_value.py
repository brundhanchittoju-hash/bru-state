from typing import Any, Optional
from app.models.document import ExtractedField


def get_effective_field_value(field: ExtractedField) -> Optional[str]:
    """
    Returns the legally effective value of an extracted field:
    if a human auditor has overridden the value, returns the corrected_value;
    otherwise returns the original extracted_value.
    """
    if field.is_overridden and field.corrected_value is not None:
        return field.corrected_value
    return field.extracted_value


def get_effective_fields_map(fields: list[ExtractedField]) -> dict[str, Any]:
    """
    Converts a list of ExtractedField models into a dictionary of field_name -> effective_value.
    """
    result: dict[str, Any] = {}
    for f in fields:
        result[f.field_name] = get_effective_field_value(f)
    return result
