from django.core.management.base import BaseCommand
from django.utils import timezone
from ghl_integration.services import TokenRefreshService, TokenHealthService


class Command(BaseCommand):
    help = 'Refresh expired or soon-to-expire GoHighLevel access tokens'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force refresh all tokens, even if not expired',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be refreshed without actually refreshing',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting GoHighLevel token refresh process...')
        )
        
        # Get token health summary
        health = TokenHealthService.get_token_health_summary()
        
        self.stdout.write(f"Token Health Summary:")
        self.stdout.write(f"  Total Integrations: {health['total_integrations']}")
        self.stdout.write(f"  Expired Tokens: {health['expired_tokens']}")
        self.stdout.write(f"  Needs Refresh: {health['needs_refresh']}")
        self.stdout.write(f"  Healthy Tokens: {health['healthy_tokens']}")
        self.stdout.write(f"  Health Percentage: {health['health_percentage']}%")
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('\nDRY RUN MODE - No tokens will be refreshed')
            )
            
            # Show what would be refreshed
            expiring_soon = TokenHealthService.get_tokens_expiring_soon(hours=24)
            if expiring_soon:
                self.stdout.write(f"\nTokens expiring within 24 hours:")
                for integration in expiring_soon:
                    self.stdout.write(f"  - {integration.location_name} ({integration.location_id})")
                    self.stdout.write(f"    Expires: {integration.expires_at}")
            return
        
        if options['force']:
            self.stdout.write(
                self.style.WARNING('\nFORCE MODE - Refreshing all tokens')
            )
        
        # Perform token refresh
        if not options['dry_run']:
            result = TokenRefreshService.refresh_expired_tokens()
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nToken refresh completed successfully!"
                    )
                )
                self.stdout.write(f"  Refreshed: {result['refreshed_count']}")
                self.stdout.write(f"  Failed: {result['failed_count']}")
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"\nToken refresh failed: {result['error']}"
                    )
                )
        
        # Show updated health summary
        if not options['dry_run'] and result.get('success'):
            updated_health = TokenHealthService.get_token_health_summary()
            self.stdout.write(f"\nUpdated Token Health:")
            self.stdout.write(f"  Health Percentage: {updated_health['health_percentage']}%")
        
        self.stdout.write(
            self.style.SUCCESS('\nGoHighLevel token refresh process completed!')
        )
