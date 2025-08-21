import logging
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import requests
from .models import GoHighLevelIntegration

logger = logging.getLogger(__name__)

# GoHighLevel OAuth configuration
GHL_CLIENT_ID = getattr(settings, 'GHL_CLIENT_ID', 'your_client_id_here')
GHL_CLIENT_SECRET = getattr(settings, 'GHL_CLIENT_SECRET', 'your_client_secret_here')
GHL_TOKEN_URL = 'https://services.leadconnectorhq.com/oauth/token'


class TokenRefreshService:
    """
    Service for automatically refreshing expired GoHighLevel access tokens
    """
    
    @staticmethod
    def refresh_expired_tokens():
        """
        Find and refresh all expired or soon-to-expire tokens
        """
        try:
            # Find integrations that need token refresh
            integrations_needing_refresh = GoHighLevelIntegration.objects.filter(
                is_active=True,
                refresh_token__isnull=False
            ).exclude(refresh_token='')
            
            refreshed_count = 0
            failed_count = 0
            
            for integration in integrations_needing_refresh:
                if integration.needs_refresh:
                    try:
                        success = TokenRefreshService.refresh_single_token(integration)
                        if success:
                            refreshed_count += 1
                            logger.info(f"Successfully refreshed token for integration {integration.id}")
                        else:
                            failed_count += 1
                            logger.error(f"Failed to refresh token for integration {integration.id}")
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Error refreshing token for integration {integration.id}: {str(e)}")
            
            logger.info(f"Token refresh completed: {refreshed_count} successful, {failed_count} failed")
            return {
                'success': True,
                'refreshed_count': refreshed_count,
                'failed_count': failed_count
            }
            
        except Exception as e:
            logger.error(f"Error in bulk token refresh: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def refresh_single_token(integration):
        """
        Refresh a single integration's access token
        """
        try:
            if not integration.refresh_token:
                logger.warning(f"No refresh token available for integration {integration.id}")
                return False
            
            # Prepare refresh request
            data = {
                'client_id': GHL_CLIENT_ID,
                'client_secret': GHL_CLIENT_SECRET,
                'grant_type': 'refresh_token',
                'refresh_token': integration.refresh_token,
                'user_type': 'Company'  # Required according to docs
            }
            
            logger.info(f"Refreshing token for integration {integration.id}")
            
            # Make refresh request
            response = requests.post(GHL_TOKEN_URL, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Update integration with new tokens
            integration.access_token = token_data['access_token']
            integration.refresh_token = token_data.get('refresh_token', integration.refresh_token)
            integration.refresh_token_id = token_data.get('refreshTokenId', integration.refresh_token_id)
            integration.expires_at = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
            integration.user_type = token_data.get('userType', integration.user_type)
            integration.scope = token_data.get('scope', integration.scope)
            integration.is_bulk_installation = token_data.get('isBulkInstallation', integration.is_bulk_installation)
            integration.save()
            
            logger.info(f"Token refreshed successfully for integration {integration.id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error refreshing token for integration {integration.id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error refreshing token for integration {integration.id}: {str(e)}")
            return False
    
    @staticmethod
    def get_valid_token(integration):
        """
        Get a valid access token, refreshing if necessary
        Returns: (token, was_refreshed) tuple
        """
        if not integration.is_active:
            raise ValueError("Integration is not active")
        
        # Check if token needs refresh
        if integration.needs_refresh:
            logger.info(f"Token for integration {integration.id} needs refresh, refreshing now")
            success = TokenRefreshService.refresh_single_token(integration)
            if not success:
                raise Exception("Failed to refresh token")
            return integration.access_token, True
        
        # Check if token is expired
        if integration.is_token_expired:
            logger.warning(f"Token for integration {integration.id} is expired, attempting refresh")
            success = TokenRefreshService.refresh_single_token(integration)
            if not success:
                raise Exception("Failed to refresh expired token")
            return integration.access_token, True
        
        # Token is valid
        return integration.access_token, False


class TokenHealthService:
    """
    Service for monitoring token health and providing insights
    """
    
    @staticmethod
    def get_token_health_summary():
        """
        Get a summary of all token health statuses
        """
        integrations = GoHighLevelIntegration.objects.filter(is_active=True)
        
        total = integrations.count()
        expired = sum(1 for i in integrations if i.is_token_expired)
        needs_refresh = sum(1 for i in integrations if i.needs_refresh)
        healthy = sum(1 for i in integrations if not i.is_token_expired and not i.needs_refresh)
        
        return {
            'total_integrations': total,
            'expired_tokens': expired,
            'needs_refresh': needs_refresh,
            'healthy_tokens': healthy,
            'health_percentage': round((healthy / total * 100) if total > 0 else 0, 2)
        }
    
    @staticmethod
    def get_tokens_expiring_soon(hours=24):
        """
        Get integrations with tokens expiring within specified hours
        """
        threshold = timezone.now() + timedelta(hours=hours)
        return GoHighLevelIntegration.objects.filter(
            is_active=True,
            expires_at__lte=threshold
        ).order_by('expires_at')
