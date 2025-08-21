import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from .services import TokenRefreshService

logger = logging.getLogger(__name__)


class GoHighLevelTokenMiddleware(MiddlewareMixin):
    """
    Middleware to automatically refresh expired GoHighLevel tokens
    This ensures API calls always use valid tokens
    """
    
    def process_request(self, request):
        """
        Process request and refresh tokens if needed
        """
        # Only process requests to GoHighLevel API endpoints
        if not self._is_ghl_api_request(request):
            return None
        
        # Check if this is a request that needs token validation
        integration_id = self._get_integration_id_from_request(request)
        if not integration_id:
            return None
        
        try:
            # Import here to avoid circular imports
            from .models import GoHighLevelIntegration
            
            integration = GoHighLevelIntegration.objects.get(id=integration_id)
            
            # Check if token needs refresh
            if integration.needs_refresh or integration.is_token_expired:
                logger.info(f"Token needs refresh for integration {integration_id}, refreshing automatically")
                
                success = TokenRefreshService.refresh_single_token(integration)
                if not success:
                    logger.error(f"Failed to refresh token for integration {integration_id}")
                    return JsonResponse({
                        'error': 'Token refresh failed',
                        'details': 'Unable to refresh expired token'
                    }, status=401)
                
                logger.info(f"Token refreshed successfully for integration {integration_id}")
            
            # Add refreshed token to request for use in views
            request.ghl_access_token = integration.access_token
            request.ghl_integration = integration
            
        except GoHighLevelIntegration.DoesNotExist:
            logger.warning(f"Integration {integration_id} not found in token middleware")
        except Exception as e:
            logger.error(f"Error in token middleware: {str(e)}")
        
        return None
    
    def _is_ghl_api_request(self, request):
        """
        Check if this request is for a GoHighLevel API endpoint
        """
        # Add your GoHighLevel API URL patterns here
        ghl_patterns = [
            '/app/api/',
            '/ghl/api/',
            '/api/ghl/',
        ]
        
        path = request.path
        return any(pattern in path for pattern in ghl_patterns)
    
    def _get_integration_id_from_request(self, request):
        """
        Extract integration ID from request
        This could be from URL parameters, headers, or request body
        """
        # Try to get from URL parameters
        integration_id = request.GET.get('integration_id') or request.POST.get('integration_id')
        
        # Try to get from headers
        if not integration_id:
            integration_id = request.headers.get('X-GHL-Integration-ID')
        
        # Try to get from JSON body
        if not integration_id and request.content_type == 'application/json':
            try:
                import json
                body_data = json.loads(request.body)
                integration_id = body_data.get('integration_id')
            except (json.JSONDecodeError, AttributeError):
                pass
        
        return integration_id


class GoHighLevelTokenHealthMiddleware(MiddlewareMixin):
    """
    Middleware to add token health information to response headers
    """
    
    def process_response(self, request, response):
        """
        Add token health headers to responses
        """
        # Only add headers to GoHighLevel API responses
        if not self._is_ghl_api_request(request):
            return response
        
        try:
            from .services import TokenHealthService
            
            health = TokenHealthService.get_token_health_summary()
            
            # Add health headers
            response['X-GHL-Token-Health'] = f"{health['health_percentage']}%"
            response['X-GHL-Total-Integrations'] = str(health['total_integrations'])
            response['X-GHL-Expired-Tokens'] = str(health['expired_tokens'])
            response['X-GHL-Needs-Refresh'] = str(health['needs_refresh'])
            
        except Exception as e:
            logger.error(f"Error adding token health headers: {str(e)}")
        
        return response
    
    def _is_ghl_api_request(self, request):
        """
        Check if this request is for a GoHighLevel API endpoint
        """
        ghl_patterns = [
            '/app/api/',
            '/ghl/api/',
            '/api/ghl/',
        ]
        
        path = request.path
        return any(pattern in path for pattern in ghl_patterns)


class GoHighLevelIframeMiddleware:
    """
    Middleware to handle iframe embedding for GoHighLevel
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if this is a GoHighLevel iframe request
        if self._is_ghl_iframe_request(request):
            # Set headers for iframe embedding
            response['X-Frame-Options'] = 'ALLOWALL'
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            
            # Add Content Security Policy for iframe embedding
            response['Content-Security-Policy'] = "frame-ancestors 'self' *.gohighlevel.com *.leadconnectorhq.com;"
        
        return response
    
    def _is_ghl_iframe_request(self, request):
        """
        Check if this is a GoHighLevel iframe request
        """
        # Check referer header
        referer = request.META.get('HTTP_REFERER', '')
        if any(domain in referer.lower() for domain in ['gohighlevel.com', 'leadconnectorhq.com']):
            return True
        
        # Check user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if 'gohighlevel' in user_agent.lower():
            return True
        
        # Check if it's an iframe request
        if request.META.get('HTTP_SEC_FETCH_DEST') == 'iframe':
            return True
        
        return False
