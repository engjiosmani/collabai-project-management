"""Versioned cache helpers for list endpoints.

Each cacheable namespace (e.g. ``"projects"``, ``"tasks"``) owns an integer
version counter. Cache keys embed that version, so bumping it on a write
atomically retires every previously cached entry without needing to scan
or enumerate keys.
"""
import hashlib

from django.core.cache import cache

# Version counters never expire — they live until explicitly cleared.
_VERSION_TIMEOUT = None


def _version_key(namespace: str) -> str:
    return f"{namespace}:version"


def get_version(namespace: str) -> int:
    key = _version_key(namespace)
    version = cache.get(key)
    if version is None:
        cache.set(key, 1, timeout=_VERSION_TIMEOUT)
        return 1
    return version


def bump_version(namespace: str) -> int:
    """Increment namespace version so new list keys do not reuse stale entries."""
    key = _version_key(namespace)
    version = get_version(namespace)
    next_version = version + 1
    cache.set(key, next_version, timeout=_VERSION_TIMEOUT)
    return next_version


def invalidate_list_cache(namespace: str, user_id, full_path: str) -> int:
    """Drop a specific cached list response and bump the namespace version."""
    cache.delete(make_list_key(namespace, user_id, full_path))
    return bump_version(namespace)


def make_list_key(namespace: str, user_id, full_path: str) -> str:
    version = get_version(namespace)
    digest = hashlib.md5(full_path.encode('utf-8')).hexdigest()
    return f"{namespace}:list:v{version}:u{user_id}:{digest}"
