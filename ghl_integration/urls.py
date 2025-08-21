from django.urls import path
from . import views

app_name = 'ghl_integration'

urlpatterns = [
    # OAuth flow
    path('install/', views.install_app, name='install_app'),
    path('callback/', views.oauth_callback, name='oauth_callback'),
    
    # Token management
    path('refresh/<uuid:integration_id>/', views.refresh_token, name='refresh_token'),
    
    # Integration management
    path('status/<uuid:integration_id>/', views.integration_status, name='integration_status'),
    path('list/', views.list_integrations, name='list_integrations'),
    
    # Webhooks
    path('webhook/', views.webhook_handler, name='webhook_handler'),
    
    # Debug/Testing
    path('test-connectivity/', views.test_connectivity, name='test_connectivity'),
    
    # Token management endpoints
    path('token-health/', views.token_health_summary, name='token_health_summary'),
    path('bulk-refresh/', views.bulk_token_refresh, name='bulk_token_refresh'),
    path('get-token/<uuid:integration_id>/', views.get_valid_token, name='get_valid_token'),
]
