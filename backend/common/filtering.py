from __future__ import annotations

import re

from django.db.models import QuerySet


def normalize_choice_value(value) -> str:
    """Normalize user-facing filter values like `in_progress` to `in progress`."""
    return re.sub(r"[_-]+", " ", str(value or "")).strip()


def filter_id_or_name(
    queryset: QuerySet,
    *,
    id_field: str,
    name_field: str,
    value,
) -> QuerySet:
    """Allow a filter to accept either a numeric id or a case-insensitive name."""
    normalized = normalize_choice_value(value)
    if not normalized:
        return queryset.none()
    if normalized.isdigit():
        return queryset.filter(**{id_field: int(normalized)})
    return queryset.filter(**{f"{name_field}__iexact": normalized})

