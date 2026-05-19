"""Versioned Redis/LocMem cache helpers for hot read endpoints.

Each cacheable namespace (e.g. ``projects``, ``tasks``) owns an integer version
counter embedded in list keys. ``bump_version`` on writes retires stale entries
without scanning Redis keys.
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterable

from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response

_VERSION_TIMEOUT = None

NAMESPACE_PROJECTS = 'projects'
NAMESPACE_TASKS = 'tasks'
NAMESPACE_WORKSPACES = 'workspaces'
NAMESPACE_ORGANIZATIONS = 'organizations'
NAMESPACE_DASHBOARD = 'dashboard'
NAMESPACE_METRICS = 'metrics'
NAMESPACE_COMMENTS = 'comments'
NAMESPACE_NOTIFICATIONS = 'notifications'
NAMESPACE_ACTIVITY_LOGS = 'activity_logs'


def get_cache_timeout() -> int:
    return int(getattr(settings, 'CACHE_DEFAULT_TIMEOUT', 300))


def get_metrics_cache_timeout() -> int:
    return int(getattr(settings, 'METRICS_CACHE_TIMEOUT', 60))


def cache_backend_label() -> str:
    backend = settings.CACHES.get('default', {}).get('BACKEND', '')
    if 'redis' in backend.lower():
        return 'redis'
    return 'locmem'


def _version_key(namespace: str) -> str:
    return f'{namespace}:version'


def get_version(namespace: str) -> int:
    key = _version_key(namespace)
    version = cache.get(key)
    if version is None:
        cache.set(key, 1, timeout=_VERSION_TIMEOUT)
        return 1
    return version


def bump_version(namespace: str) -> int:
    key = _version_key(namespace)
    next_version = get_version(namespace) + 1
    cache.set(key, next_version, timeout=_VERSION_TIMEOUT)
    return next_version


def bump_versions(namespaces: Iterable[str]) -> None:
    for namespace in namespaces:
        bump_version(namespace)


def bump_dashboard_cache() -> int:
    return bump_version(NAMESPACE_DASHBOARD)


def invalidate_list_cache(namespace: str, user_id, full_path: str) -> int:
    cache.delete(make_list_key(namespace, user_id, full_path))
    return bump_version(namespace)


def make_list_key(namespace: str, user_id, full_path: str) -> str:
    version = get_version(namespace)
    digest = hashlib.md5(full_path.encode('utf-8')).hexdigest()
    return f'{namespace}:list:v{version}:u{user_id}:{digest}'


def make_fixed_key(namespace: str, suffix: str) -> str:
    version = get_version(namespace)
    return f'{namespace}:fixed:v{version}:{suffix}'


def get_cached_payload(key: str) -> Any | None:
    return cache.get(key)


def set_cached_payload(key: str, data: Any, *, timeout: int | None = None) -> None:
    cache.set(key, data, timeout=timeout if timeout is not None else get_cache_timeout())


class CachedListMixin:
    """Cache GET list responses per user + query string."""

    cache_namespace: str = ''
    cache_default_list_path: str = ''

    def list(self, request, *args, **kwargs):
        cache_key = make_list_key(
            self.cache_namespace,
            request.user.pk,
            request.get_full_path(),
        )
        cached = get_cached_payload(cache_key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200:
            set_cached_payload(cache_key, response.data)
        return response

    def invalidate_list_cache_for_request(self) -> None:
        request = getattr(self, 'request', None)
        user = getattr(request, 'user', None) if request else None
        if user is not None and getattr(user, 'is_authenticated', False):
            paths = set()
            if self.cache_default_list_path:
                paths.add(self.cache_default_list_path)
            if request is not None:
                paths.add(request.get_full_path())
            for path in paths:
                invalidate_list_cache(self.cache_namespace, user.pk, path)
        else:
            bump_version(self.cache_namespace)


class CachedGETMixin:
    """Cache successful GET handlers on APIView subclasses."""

    cache_namespace: str = ''
    cache_path_suffix: str = ''

    def get_cache_key(self, request) -> str:
        path = self.cache_path_suffix or request.get_full_path()
        return make_list_key(self.cache_namespace, request.user.pk, path)

    def get_cached_response(self, request):
        cached = get_cached_payload(self.get_cache_key(request))
        if cached is not None:
            return Response(cached)
        return None

    def cache_response(self, request, response: Response) -> Response:
        if response.status_code == 200:
            set_cached_payload(self.get_cache_key(request), response.data)
        return response
