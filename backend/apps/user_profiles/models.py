import uuid as _uuid
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from common.models import BaseModel
from apps.organizations.models import Organization
User = get_user_model()
class Profile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles"
    )
    bio = models.TextField(blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    def __str__(self):
        return f"Profile of {self.user.username}"
class PasswordResetToken(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
    )
    token = models.UUIDField(default=_uuid.uuid4, unique=True, editable=False)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f'PasswordResetToken({self.user.username}, used={self.is_used})'
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at