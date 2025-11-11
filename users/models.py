# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # Extra fields
    status = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    allowed_ips = models.JSONField(blank=True, null=True)
    roles = models.JSONField(blank=True, null=True)
    teams = models.JSONField(blank=True, null=True)
    tags = models.JSONField(blank=True, null=True)

    # Marketing / Attribution Data
    campaign_id = models.CharField(max_length=255, null=True, blank=True)
    campaign_name = models.CharField(max_length=255, null=True, blank=True)
    source = models.CharField(max_length=255, null=True, blank=True)  # utm_source
    medium = models.CharField(max_length=255, null=True, blank=True)  # utm_medium
    gclid = models.CharField(max_length=255, null=True, blank=True)  # Google Click ID
    fbclid = models.CharField(
        max_length=255, null=True, blank=True
    )  # Facebook Click ID

    landing_page = models.URLField(max_length=2000, null=True, blank=True)
    referrer_url = models.URLField(max_length=2000, null=True, blank=True)

    user_agent = models.CharField(max_length=512, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Optional – store future dynamic fields like TikTok, Bing, HubSpot
    extra_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.username or self.email

    # ✅ Map your naming to Django's built-in logic
    @property
    def is_admin(self):
        return self.is_staff

    @is_admin.setter
    def is_admin(self, value):
        self.is_staff = value

    def __str__(self):
        return self.username or self.email
