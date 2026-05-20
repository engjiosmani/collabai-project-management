from django.contrib.auth import get_user_model
from django.db import models

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