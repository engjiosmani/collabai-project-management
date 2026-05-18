from django.db import IntegrityError
from rest_framework import serializers

from .models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    workspace_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = (
            'id',
            'name',
            'description',
            'workspace_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('workspace_count', 'created_at', 'updated_at')

    def validate_name(self, value: str):
        text = (value or '').strip()
        if not text:
            raise serializers.ValidationError('This field may not be blank.')
        qs = Organization.objects.filter(name__iexact=text)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('An organization with this name already exists.')
        return text

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': 'An organization with this name already exists.'})

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': 'An organization with this name already exists.'})


