from django.urls import path
from . import views

app_name = 'ghl_integration'

urlpatterns = [
    # OAuth flow
    path('install/', views.install_app, name='install_app'),
    path('callback/', views.oauth_callback, name='oauth_callback'),
    
    # App landing page (main app interface)
    path('', views.ghl_app_integration, name='app_landing'),
    
    # Legacy app landing page (moved to different URL)
    path('landing/', views.app_landing, name='app_landing_legacy'),
    
    # GoHighLevel app integration (sidebar/app integration)
    path('ghl-integration/', views.ghl_app_integration, name='ghl_app_integration'),
    
    # App manifest (for GoHighLevel app installation)
    path('manifest.json', views.app_manifest, name='app_manifest'),
    
    # Sidebar integration (for GoHighLevel to embed app)
    path('sidebar/', views.sidebar_integration, name='sidebar_integration'),
    
    # Sidebar widget (for custom sidebar widgets)
    path('sidebar-widget/', views.sidebar_widget, name='sidebar_widget'),
    
    # Test iframe (for debugging iframe embedding)
    path('test-iframe/', views.test_iframe, name='test_iframe'),
    path('postmessage-test/', views.postmessage_test, name='postmessage_test'),
    
    # User identification API
    path('user-identification/', views.user_identification, name='user_identification'),
    path('logout/', views.logout_user, name='logout_user'),
    path('check-session/', views.check_session, name='check_session'),
    
    # Token management
    path('refresh/<uuid:integration_id>/', views.refresh_token, name='refresh_token'),
    path('status/<uuid:integration_id>/', views.integration_status, name='integration_status'),
    
    # Integration management
    path('list/', views.list_integrations, name='list_integrations'),
    path('webhook/', views.webhook_handler, name='webhook_handler'),
    
    # Token health and management
    path('token-health/', views.token_health_summary, name='token_health_summary'),
    path('bulk-refresh/', views.bulk_token_refresh, name='bulk_token_refresh'),
    path('get-token/<uuid:integration_id>/', views.get_valid_token, name='get_valid_token'),
    
    # Testing and debugging
    path('test-connectivity/', views.test_connectivity, name='test_connectivity'),
    path('whatsapp-token/', views.manage_whatsapp_token, name='manage_whatsapp_token'),
]
