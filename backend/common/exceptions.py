"""Custom DRF exception handler for CollabAI.

Wraps DRF's default ``exception_handler`` so that every API error:

- Carries the request's ``X-Request-ID`` in both the response header and the
  JSON body, giving administrators a clean handle to trace the incident in
  backend logs.
- For unhandled (non-DRF) exceptions, returns a sanitized JSON 500 payload
  when ``DEBUG=False`` (Django's default error page is replaced) and the full
  exception message when ``DEBUG=True`` for easier local troubleshooting.
"""

import logging
import uuid

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def _request_id_from_context(context) -> str:
    request = context.get('request') if context else None
    rid = getattr(request, 'request_id', None) if request is not None else None
    return str(rid) if rid else str(uuid.uuid4())


def custom_exception_handler(exc, context):
    """DRF exception handler that adds X-Request-ID and sanitizes 500 errors."""
    response = exception_handler(exc, context)
    request_id = _request_id_from_context(context)

    if response is None:
        logger.exception(
            'Unhandled server exception request_id=%s exc=%s',
            request_id,
            exc.__class__.__name__,
        )
        detail = (
            str(exc)
            if getattr(settings, 'DEBUG', False)
            else 'A server error occurred.'
        )
        response = Response(
            {'detail': detail, 'request_id': request_id},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    response['X-Request-ID'] = request_id
    return response
