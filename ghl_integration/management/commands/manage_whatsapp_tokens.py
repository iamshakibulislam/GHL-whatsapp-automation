from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from ghl_integration.models import WhatsAppAccessToken, GoHighLevelIntegration
from datetime import timedelta


class Command(BaseCommand):
    help = 'Manage WhatsApp access tokens for GoHighLevel integrations'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['list', 'create', 'update', 'delete', 'status', 'cleanup'],
            help='Action to perform on WhatsApp tokens'
        )
        parser.add_argument(
            '--location-id',
            type=str,
            help='GoHighLevel location ID for the token'
        )
        parser.add_argument(
            '--token',
            type=str,
            help='Access token value'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force action without confirmation'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'list':
            self.list_tokens()
        elif action == 'create':
            self.create_token(options)
        elif action == 'update':
            self.update_token(options)
        elif action == 'delete':
            self.delete_token(options)
        elif action == 'status':
            self.check_status(options)
        elif action == 'cleanup':
            self.cleanup_tokens()

    def list_tokens(self):
        """List all WhatsApp access tokens"""
        tokens = WhatsAppAccessToken.objects.all().select_related('integration')
        
        if not tokens:
            self.stdout.write(self.style.WARNING('No WhatsApp access tokens found.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {tokens.count()} WhatsApp access token(s):'))
        self.stdout.write('')
        
        for token in tokens:
            self.stdout.write(f'🔑 Token ID: {token.id}')
            self.stdout.write(f'   Location: {token.integration.location_name} ({token.integration.location_id})')
            self.stdout.write(f'   Access Token: {token.access_token[:20]}...' if len(token.access_token) > 20 else f'   Access Token: {token.access_token}')
            self.stdout.write(f'   Created: {token.created_at}')
            self.stdout.write('')

    def create_token(self, options):
        """Create a new WhatsApp access token"""
        location_id = options['location_id']
        token_value = options['token']
        
        if not all([location_id, token_value]):
            raise CommandError('--location-id and --token are required for creation')
        
        # Check if integration exists
        try:
            integration = GoHighLevelIntegration.objects.get(location_id=location_id)
        except GoHighLevelIntegration.DoesNotExist:
            raise CommandError(f'No GoHighLevel integration found for location ID: {location_id}')
        
        # Check if token already exists
        if WhatsAppAccessToken.objects.filter(integration=integration).exists():
            raise CommandError(f'WhatsApp access token already exists for location: {location_id}')
        
        # Calculate expiration if provided
        expires_at = None
        if options['expires_in']:
            expires_at = timezone.now() + timedelta(hours=options['expires_in'])
        
        # Create the token
        token = WhatsAppAccessToken.objects.create(
            integration=integration,
            access_token=token_value
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ WhatsApp access token created successfully!'
            )
        )
        self.stdout.write(f'   Token ID: {token.id}')
        self.stdout.write(f'   Location: {integration.location_name} ({integration.location_id})')

    def update_token(self, options):
        """Update an existing WhatsApp access token"""
        location_id = options['location_id']
        
        if not location_id:
            raise CommandError('--location-id is required for updates')
        
        try:
            integration = GoHighLevelIntegration.objects.get(location_id=location_id)
            token = WhatsAppAccessToken.objects.get(integration=integration)
        except (GoHighLevelIntegration.DoesNotExist, WhatsAppAccessToken.DoesNotExist):
            raise CommandError(f'No WhatsApp access token found for location ID: {location_id}')
        
        # Update fields if provided
        updated_fields = []
        
        if options['token']:
            token.access_token = options['token']
            updated_fields.append('access_token')
        
        if updated_fields:
            token.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ WhatsApp access token updated successfully!'
                )
            )
            self.stdout.write(f'   Updated fields: {", ".join(updated_fields)}')
        else:
            self.stdout.write(self.style.WARNING('No fields to update.'))

    def delete_token(self, options):
        """Delete a WhatsApp access token"""
        location_id = options['location_id']
        
        if not location_id:
            raise CommandError('--location-id is required for deletion')
        
        try:
            integration = GoHighLevelIntegration.objects.get(location_id=location_id)
            token = WhatsAppAccessToken.objects.get(integration=integration)
        except (GoHighLevelIntegration.DoesNotExist, WhatsAppAccessToken.DoesNotExist):
            raise CommandError(f'No WhatsApp access token found for location ID: {location_id}')
        
        if not options['force']:
            confirm = input(f'Are you sure you want to delete the WhatsApp token for location {location_id}? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Deletion cancelled.')
                return
        
        token.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ WhatsApp access token deleted successfully for location: {location_id}'
            )
        )

    def check_status(self, options):
        """Check status of WhatsApp access tokens"""
        location_id = options['location_id']
        
        if location_id:
            # Check specific location
            try:
                integration = GoHighLevelIntegration.objects.get(location_id=location_id)
                tokens = WhatsAppAccessToken.objects.filter(integration=integration)
            except GoHighLevelIntegration.DoesNotExist:
                raise CommandError(f'No GoHighLevel integration found for location ID: {location_id}')
        else:
            # Check all tokens
            tokens = WhatsAppAccessToken.objects.all()
        
        if not tokens:
            self.stdout.write(self.style.WARNING('No WhatsApp access tokens found.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'WhatsApp Token Status Report:'))
        self.stdout.write('')
        
        for token in tokens:
            self.stdout.write(f'✅ Found - {token.integration.location_name} ({token.integration.location_id})')
        
        self.stdout.write('')
        self.stdout.write(f'Summary: {tokens.count()} tokens found')

    def cleanup_tokens(self):
        """Clean up tokens from inactive integrations"""
        # Find tokens for inactive integrations
        inactive_integration_tokens = WhatsAppAccessToken.objects.filter(
            integration__is_active=False
        )
        
        total_to_clean = inactive_integration_tokens.count()
        
        if total_to_clean == 0:
            self.stdout.write(self.style.SUCCESS('No tokens need cleanup.'))
            return
        
        self.stdout.write(f'Found {total_to_clean} tokens to clean up:')
        self.stdout.write(f'  - {total_to_clean} tokens from inactive integrations')
        
        if not options.get('force'):
            confirm = input('Proceed with cleanup? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Cleanup cancelled.')
                return
        
        # Perform cleanup
        inactive_deleted = inactive_integration_tokens.count()
        inactive_integration_tokens.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Cleanup completed! Deleted {inactive_deleted} tokens from inactive integrations.'
            )
        )
