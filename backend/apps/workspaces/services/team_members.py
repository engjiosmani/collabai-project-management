from __future__ import annotations

from apps.organizations.models import OrganizationMember
from apps.workspaces.models import TeamMember


def team_members_payload_for_organization(organization_id: int) -> list[dict]:
    """Build team_members list for Task Generator API / AI prompts."""
    members = (
        OrganizationMember.objects.filter(organization_id=organization_id)
        .select_related('user', 'job_role')
        .order_by('user__email')
    )
    if not members.exists():
        members = (
            TeamMember.objects.filter(workspace__organization_id=organization_id)
            .select_related('user', 'job_role')
            .order_by('user__email')
        )
    payload = []
    for member in members:
        job = member.job_role
        payload.append(
            {
                'user_id': member.user_id,
                'username': member.user.username or member.user.email.split('@')[0],
                'role': job.name if job else 'Team Member',
                'job_role_code': job.code if job else None,
                'job_role_id': job.pk if job else None,
                'task_categories': list(job.task_categories) if job else [],
            }
        )
    return payload


team_members_payload_for_workspace = team_members_payload_for_organization
