from django.db import models
from django.utils import timezone
import uuid


class GoHighLevelIntegration(models.Model):
    """
    Model to store GoHighLevel app installation data and access tokens
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location_id = models.CharField(max_length=255, unique=True, help_text="GoHighLevel location ID")
    location_name = models.CharField(max_length=255, blank=True, help_text="GoHighLevel location name")
    user_id = models.CharField(max_length=255, blank=True, help_text="GoHighLevel user ID")
    user_email = models.EmailField(blank=True, help_text="GoHighLevel user email")
    
    # OAuth tokens - Complete GoHighLevel token storage
    access_token = models.TextField(help_text="GoHighLevel access token")
    refresh_token = models.TextField(blank=True, help_text="GoHighLevel refresh token")
    refresh_token_id = models.CharField(max_length=255, blank=True, help_text="GoHighLevel refresh token ID")
    token_type = models.CharField(max_length=50, default="Bearer", help_text="Token type")
    expires_at = models.DateTimeField(help_text="Token expiration time")
    
    # Token metadata from GoHighLevel response
    user_type = models.CharField(max_length=50, blank=True, help_text="Token user type (Company/Location)")
    scope = models.TextField(blank=True, help_text="OAuth scopes granted")
    is_bulk_installation = models.BooleanField(default=False, help_text="Whether this is a bulk installation")
    
    # Installation metadata
    installed_at = models.DateTimeField(default=timezone.now, help_text="When the app was installed")
    last_used_at = models.DateTimeField(auto_now=True, help_text="Last time the integration was used")
    is_active = models.BooleanField(default=True, help_text="Whether the integration is active")
    
    # Additional GoHighLevel data
    company_id = models.CharField(max_length=255, blank=True, help_text="GoHighLevel company ID")
    company_name = models.CharField(max_length=255, blank=True, help_text="Company name")
    phone = models.CharField(max_length=50, blank=True, help_text="Company phone")
    website = models.URLField(blank=True, help_text="Company website")
    
    class Meta:
        db_table = 'ghl_integration'
        verbose_name = 'GoHighLevel Integration'
        verbose_name_plural = 'GoHighLevel Integrations'
        ordering = ['-installed_at']
    
    def __str__(self):
        return f"{self.location_name or self.location_id} - {self.user_email or 'Unknown User'}"
    
    @property
    def is_token_expired(self):
        """Check if the access token has expired"""
        return timezone.now() >= self.expires_at
    
    @property
    def needs_refresh(self):
        """Check if token needs refresh (expires within 1 hour)"""
        return (self.expires_at - timezone.now()) <= timezone.timedelta(hours=1)


class GoHighLevelWebhook(models.Model):
    """
    Model to store webhook events from GoHighLevel
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(GoHighLevelIntegration, on_delete=models.CASCADE, related_name='webhooks')
    event_type = models.CharField(max_length=100, help_text="Type of webhook event")
    event_data = models.JSONField(help_text="Webhook event data")
    received_at = models.DateTimeField(default=timezone.now, help_text="When webhook was received")
    processed = models.BooleanField(default=False, help_text="Whether webhook was processed")
    
    class Meta:
        db_table = 'ghl_webhook'
        verbose_name = 'GoHighLevel Webhook'
        verbose_name_plural = 'GoHighLevel Webhooks'
        ordering = ['-received_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.integration.location_name} - {self.received_at}"
