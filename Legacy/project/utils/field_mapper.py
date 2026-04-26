FIELD_MAP = {
    "source_of_funds": "fund_source",
    "borrowing_source": "fund_source",

    "borrowing_type": "term_type",
    "borrowing_term": "term_type",

    "borrower_type": "borrower_type"
}


def normalize_field(field: str) -> str:
    field = field.lower().strip()
    return FIELD_MAP.get(field, field)