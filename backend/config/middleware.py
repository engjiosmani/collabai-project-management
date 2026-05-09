import logging
import time
import uuid

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.permissions import user_matches_any_required_role
from common.utils import client_ip

logger = logging.getLogger(__name__)


def _normalize_path(path: str) -> str:
    if not path:
        return '/'
    path = '/' + path.lstrip('/')
    if len(path) > 1 and path.endswith('/'):
        path = path.rstrip('/')
    return path


def _jwt_role_rules():
    raw = getattr(settings, 'API_JWT_ROLE_REQUIREMENTS', ())
    return tuple(raw)


def _longest_matching_roles(path: str) -> tuple:
    """Pick role names for the longest matching path prefix."""
    pn = _normalize_path(path)
    matches = ()
    best = -1
    for prefix, roles in _jwt_role_rules():
        pfx = _normalize_path(prefix)
        if pn == pfx or pn.startswith(pfx + '/'):
            ln = len(pfx)
            if ln > best:
                best = ln
                matches = tuple(roles or ())
    return matches


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        request.request_id = request_id
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000
        user = getattr(request, 'user', None)
        user_id = getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else '-'
        response['X-Request-ID'] = request_id
        logger.info(
            'request_id=%s method=%s endpoint=%s user_id=%s status=%s duration_ms=%.2f ip=%s',
            request_id,
            request.method,
            request.path,
            user_id,
            getattr(response, 'status_code', '?'),
            duration_ms,
            client_ip(request) or '-',
        )
        return response


class JWTAuthenticationMiddleware:
    """Enforce Bearer JWT on versioned API routes and attach ``request.user`` for logging & DRF parity.

    Public routes (registration, login, refresh) optionally authenticate without rejecting invalid tokens.
    Optional path-prefix RBAC uses ``settings.API_JWT_ROLE_REQUIREMENTS`` with
    :func:`common.permissions.user_matches_any_required_role`.
    """

    jwt_auth = JWTAuthentication()

    def __init__(self, get_response):
        self.get_response = get_response

    def _public_paths(self) -> tuple:
        return tuple(getattr(settings, 'API_JWT_PUBLIC_PATHS', ()) or (
            '/api/v1/auth/register',
            '/api/v1/auth/login',
            '/api/v1/auth/refresh',
        ))

    def _is_public_path(self, path: str) -> bool:
        pn = _normalize_path(path)
        return pn in {_normalize_path(p) for p in self._public_paths()}

    def _apply_jwt_optional(self, request):
        raw = Request(request)
        if not raw.headers.get('Authorization', '').startswith('Bearer '):
            return
        try:
            outcome = self.jwt_auth.authenticate(raw)
            if outcome:
                request.user, request.auth = outcome
        except AuthenticationFailed:
            pass

    def _apply_jwt_required(self, request):
        raw = Request(request)
        try:
            outcome = self.jwt_auth.authenticate(raw)
        except AuthenticationFailed:
            return JsonResponse(
                {'detail': 'Given token not valid for any token type'},
                status=401,
            )
        if outcome is None:
            return JsonResponse(
                {'detail': 'Authentication credentials were not provided.'},
                status=401,
            )
        user, token = outcome
        request.user = user
        request.auth = token

        required_roles = _longest_matching_roles(request.path)
        if required_roles and not user_matches_any_required_role(user, required_roles):
            return JsonResponse(
                {'detail': 'You do not have permission to perform this action.'},
                status=403,
            )
        return None

    def __call__(self, request):
        prefix = getattr(settings, 'API_JWT_ENFORCE_PREFIX', '/api/v1/').rstrip('/') or '/'
        if not (request.path == prefix or request.path.startswith(prefix + '/')):
            return self.get_response(request)

        # CORS preflight: avoid DRF auth on OPTIONS (would 401 before CORS can answer).
        if request.method == 'OPTIONS':
            resp = HttpResponse(status=204)
            rid = getattr(request, 'request_id', None) or str(uuid.uuid4())
            resp['X-Request-ID'] = str(rid)
            return resp

        if self._is_public_path(request.path):
            self._apply_jwt_optional(request)
            return self.get_response(request)

        early = self._apply_jwt_required(request)
        if early is not None:
            rid = getattr(request, 'request_id', None) or str(uuid.uuid4())
            early['X-Request-ID'] = str(rid)
            return early
        return self.get_response(request)
