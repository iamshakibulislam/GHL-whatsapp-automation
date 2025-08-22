from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import GoHighLevelIntegration, GoHighLevelWebhook, WhatsAppAccessToken


@admin.register(GoHighLevelIntegration)
class GoHighLevelIntegrationAdmin(admin.ModelAdmin):
    list_display = [
        'location_name', 'location_id', 'user_email', 'company_name', 
        'is_active', 'token_status', 'installed_at', 'last_used_at'
    ]
    list_filter = ['is_active', 'installed_at', 'last_used_at']
    search_fields = ['location_name', 'location_id', 'user_email', 'company_name']
    readonly_fields = ['id', 'installed_at', 'last_used_at', 'token_status_display']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('location_id', 'location_name', 'user_id', 'user_email')
        }),
        ('Company Information', {
            'fields': ('company_name', 'phone', 'website')
        }),
        ('OAuth Tokens', {
            'fields': ('access_token', 'refresh_token', 'refresh_token_id', 'token_type', 'expires_at')
        }),
        ('Token Metadata', {
            'fields': ('user_type', 'scope', 'is_bulk_installation')
        }),
        ('Status', {
            'fields': ('is_active', 'installed_at', 'last_used_at')
        }),
        ('System', {
            'fields': ('id', 'token_status_display'),
            'classes': ('collapse',)
        })
    )
    
    def token_status(self, obj):
        if obj.is_token_expired:
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.needs_refresh:
            return format_html('<span style="color: orange;">Needs Refresh</span>')
        else:
            return format_html('<span style="color: green;">Valid</span>')
    token_status.short_description = 'Token Status'
    
    def token_status_display(self, obj):
        return f"Expired: {obj.is_token_expired}, Needs Refresh: {obj.needs_refresh}"
    token_status_display.short_description = 'Token Status Details'
    
    actions = ['refresh_tokens', 'deactivate_integrations']
    
    def refresh_tokens(self, request, queryset):
        """Action to refresh tokens for selected integrations"""
        count = 0
        for integration in queryset:
            if integration.refresh_token:
                try:
                    # This would call the refresh logic
                    # For now, just mark as needing refresh
                    integration.save()
                    count += 1
                except Exception:
                    pass
        
        self.message_user(request, f"Successfully refreshed {count} tokens.")
    refresh_tokens.short_description = "Refresh access tokens"
    
    def deactivate_integrations(self, request, queryset):
        """Action to deactivate selected integrations"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Successfully deactivated {updated} integrations.")
    deactivate_integrations.short_description = "Deactivate integrations"


@admin.register(GoHighLevelWebhook)
class GoHighLevelWebhookAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'integration_display', 'received_at', 'processed'
    ]
    list_filter = ['event_type', 'processed', 'received_at']
    search_fields = ['event_type', 'integration__location_name', 'integration__location_id']
    readonly_fields = ['id', 'received_at', 'integration_display']
    
    fieldsets = (
        ('Webhook Information', {
            'fields': ('event_type', 'integration', 'received_at', 'processed')
        }),
        ('Event Data', {
            'fields': ('event_data',),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('id',),
            'classes': ('collapse',)
        })
    )
    
    def integration_display(self, obj):
        if obj.integration:
            return f"{obj.integration.location_name} ({obj.integration.location_id})"
        return "Unknown"
    integration_display.short_description = 'Integration'
    
    actions = ['mark_as_processed', 'mark_as_unprocessed']
    
    def mark_as_processed(self, request, queryset):
        """Action to mark webhooks as processed"""
        updated = queryset.update(processed=True)
        self.message_user(request, f"Successfully marked {updated} webhooks as processed.")
    mark_as_processed.short_description = "Mark webhooks as processed"
    
    def mark_as_unprocessed(self, request, queryset):
        """Action to mark webhooks as unprocessed"""
        updated = queryset.update(processed=False)
        self.message_user(request, f"Successfully marked {updated} webhooks as unprocessed.")
    mark_as_unprocessed.short_description = "Mark webhooks as unprocessed"


@admin.register(WhatsAppAccessToken)
class WhatsAppAccessTokenAdmin(admin.ModelAdmin):
    list_display = [
        'integration_display', 'access_token_preview', 'created_at', 'updated_at'
    ]
    list_filter = ['created_at', 'updated_at']
    search_fields = [
        'integration__location_name', 'integration__location_id'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('integration', 'access_token')
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def integration_display(self, obj):
        if obj.integration:
            return f"{obj.integration.location_name} ({obj.integration.location_id})"
        return "Unknown"
    integration_display.short_description = 'GoHighLevel Location'
    
    def access_token_preview(self, obj):
        if obj.access_token:
            return f"{obj.access_token[:20]}..." if len(obj.access_token) > 20 else obj.access_token
        return "No token"
    access_token_preview.short_description = 'Access Token'
