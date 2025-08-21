import logging
from django.utils import timezone
from .services import TokenRefreshService, TokenHealthService
from .models import GoHighLevelIntegration

logger = logging.getLogger(__name__)


# Standalone functions for manual cron execution
def refresh_expired_tokens():
    """
    Standalone function to refresh expired tokens
    Can be called from Django shell or other cron systems
    """
    try:
        logger.info("Manual execution of refresh_expired_tokens")
        result = TokenRefreshService.refresh_expired_tokens()
        
        if result['success']:
            logger.info(
                f"Manual token refresh completed: "
                f"{result['refreshed_count']} refreshed, "
                f"{result['failed_count']} failed"
            )
        else:
            logger.error(f"Manual token refresh failed: {result['error']}")
            
        return result
        
    except Exception as e:
        logger.error(f"Error in manual token refresh: {str(e)}")
        return {'success': False, 'error': str(e)}


def daily_token_health_check():
    """
    Standalone function for daily token health check
    Can be called from Django shell or other cron systems
    """
    try:
        logger.info("Starting daily token health check cron job")
        
        # Get comprehensive health summary
        health = TokenHealthService.get_token_health_summary()
        
        # Log health metrics
        logger.info(
            f"Daily Token Health Report - "
            f"Total: {health['total_integrations']}, "
            f"Healthy: {health['healthy_tokens']}, "
            f"Expired: {health['expired_tokens']}, "
            f"Needs Refresh: {health['needs_refresh']}, "
            f"Health: {health['health_percentage']}%"
        )
        
        # Find integrations with severely expired tokens (more than 7 days)
        from datetime import timedelta
        severely_expired_threshold = timezone.now() - timedelta(days=7)
        severely_expired = GoHighLevelIntegration.objects.filter(
            is_active=True,
            expires_at__lt=severely_expired_threshold
        )
        
        if severely_expired.exists():
            logger.warning(
                f"Found {severely_expired.count()} integrations with severely expired tokens "
                f"(older than 7 days). These may need manual intervention."
            )
            
            for integration in severely_expired:
                logger.warning(
                    f"Severely expired integration: {integration.location_name} "
                    f"({integration.location_id}) - Expired: {integration.expires_at}"
                )
        
        # Find integrations that haven't been used recently (more than 30 days)
        unused_threshold = timezone.now() - timedelta(days=30)
        unused_integrations = GoHighLevelIntegration.objects.filter(
            is_active=True,
            last_used_at__lt=unused_threshold
        )
        
        if unused_integrations.exists():
            logger.info(
                f"Found {unused_integrations.count()} integrations that haven't been used "
                f"in the last 30 days. Consider reviewing these for deactivation."
            )
        
        logger.info("Daily token health check cron job completed successfully")
        return health
        
    except Exception as e:
        logger.error(f"Error in daily token health check cron job: {str(e)}")
        return {'error': str(e)}


def weekly_bulk_refresh():
    """
    Standalone function for weekly bulk refresh
    Can be called from Django shell or other cron systems
    """
    try:
        logger.info("Starting weekly bulk token refresh cron job")
        
        # Get all active integrations
        active_integrations = GoHighLevelIntegration.objects.filter(is_active=True)
        
        if not active_integrations.exists():
            logger.info("No active integrations found for weekly bulk refresh")
            return {'success': True, 'refreshed_count': 0, 'failed_count': 0}
        
        logger.info(f"Found {active_integrations.count()} active integrations for weekly refresh")
        
        # Perform bulk refresh
        result = TokenRefreshService.refresh_expired_tokens()
        
        if result['success']:
            logger.info(
                f"Weekly bulk refresh completed: "
                f"{result['refreshed_count']} refreshed, "
                f"{result['failed_count']} failed"
            )
            
            # Get updated health summary
            updated_health = TokenHealthService.get_token_health_summary()
            logger.info(
                f"Weekly bulk refresh health update: "
                f"Health percentage improved to {updated_health['health_percentage']}%"
            )
        else:
            logger.error(f"Weekly bulk refresh failed: {result['error']}")
        
        logger.info("Weekly bulk token refresh cron job completed")
        return result
        
    except Exception as e:
        logger.error(f"Error in weekly bulk refresh cron job: {str(e)}")
        return {'success': False, 'error': str(e)}
