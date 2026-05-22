def write_audit_log(user, action, entity_name, entity_id=None, metadata=None):
    """Best-effort append-only audit entry for security-sensitive actions."""
    from .models import AuditLog

    try:
        AuditLog.objects.create(
            user=user if getattr(user, 'is_authenticated', False) else None,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            metadata=metadata or {},
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            'Failed to write audit log for %s %s', entity_name, action
        )
