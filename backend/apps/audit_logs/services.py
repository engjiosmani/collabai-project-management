def write_audit_log(user, action, entity_name, entity_id=None, metadata=None, organization=None):
    """Best-effort append-only audit entry for security-sensitive actions."""
    from .models import AuditLog

    try:
        metadata = metadata or {}
        organization_id = getattr(organization, 'pk', organization)
        if organization_id is None:
            organization_id = metadata.get('organization_id')
        AuditLog.objects.create(
            user=user if getattr(user, 'is_authenticated', False) else None,
            organization_id=organization_id,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            metadata=metadata,
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            'Failed to write audit log for %s %s', entity_name, action
        )
