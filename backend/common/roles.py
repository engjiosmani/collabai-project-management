from apps.workspaces.models import TeamMember


def get_user_role(user, workspace):

    membership = TeamMember.objects.filter(
        user=user,
        workspace=workspace
    ).select_related("role").first()

    if not membership:
        return None

    if not membership.role:
        return None

    return membership.role.name