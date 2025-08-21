#!/usr/bin/env python
"""
Demo script for GoHighLevel Integration App

This script demonstrates how to use the GoHighLevel integration system.
Run this after setting up the Django app and database.
"""

import os
import sys
import django
from datetime import timedelta

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatreach.settings')
django.setup()

from ghl_integration.models import GoHighLevelIntegration, GoHighLevelWebhook
from django.utils import timezone


def demo_integration_creation():
    """Demonstrate creating a GoHighLevel integration"""
    print("=== Creating Sample GoHighLevel Integration ===\n")
    
    # Create a sample integration
    integration = GoHighLevelIntegration.objects.create(
        location_id='demo_location_123',
        location_name='Demo Business',
        user_id='demo_user_456',
        user_email='demo@business.com',
        access_token='demo_access_token_789',
        refresh_token='demo_refresh_token_101',
        expires_at=timezone.now() + timedelta(hours=24),
        company_name='Demo Company Inc.',
        phone='555-123-4567',
        website='https://democompany.com'
    )
    
    print(f"Created integration: {integration}")
    print(f"Location ID: {integration.location_id}")
    print(f"Company: {integration.company_name}")
    print(f"User: {integration.user_email}")
    print(f"Token expires: {integration.expires_at}")
    print(f"Token expired: {integration.is_token_expired}")
    print(f"Needs refresh: {integration.needs_refresh}")
    print(f"Active: {integration.is_active}")
    
    return integration


def demo_webhook_creation(integration):
    """Demonstrate creating webhook events"""
    print("\n=== Creating Sample Webhook Events ===\n")
    
    # Create sample webhook events
    webhook1 = GoHighLevelWebhook.objects.create(
        integration=integration,
        event_type='app.installed',
        event_data={
            'eventType': 'app.installed',
            'locationId': integration.location_id,
            'timestamp': timezone.now().isoformat()
        }
    )
    
    webhook2 = GoHighLevelWebhook.objects.create(
        integration=integration,
        event_type='contact.created',
        event_data={
            'eventType': 'contact.created',
            'locationId': integration.location_id,
            'contactId': 'contact_123',
            'timestamp': timezone.now().isoformat()
        }
    )
    
    print(f"Created webhook 1: {webhook1}")
    print(f"Event type: {webhook1.event_type}")
    print(f"Event data: {webhook1.event_data}")
    
    print(f"\nCreated webhook 2: {webhook2}")
    print(f"Event type: {webhook2.event_type}")
    print(f"Event data: {webhook2.event_data}")
    
    return [webhook1, webhook2]


def demo_token_management(integration):
    """Demonstrate token management features"""
    print("\n=== Token Management Demo ===\n")
    
    print("Current token status:")
    print(f"  Expires at: {integration.expires_at}")
    print(f"  Is expired: {integration.is_token_expired}")
    print(f"  Needs refresh: {integration.needs_refresh}")
    
    # Simulate token expiration
    print("\nSimulating token expiration...")
    integration.expires_at = timezone.now() - timedelta(hours=1)
    integration.save()
    
    print("After expiration:")
    print(f"  Is expired: {integration.is_token_expired}")
    print(f"  Needs refresh: {integration.needs_refresh}")
    
    # Simulate token near expiration
    print("\nSimulating token near expiration...")
    integration.expires_at = timezone.now() + timedelta(minutes=30)
    integration.save()
    
    print("Near expiration:")
    print(f"  Is expired: {integration.is_token_expired}")
    print(f"  Needs refresh: {integration.needs_refresh}")
    
    # Reset to valid token
    integration.expires_at = timezone.now() + timedelta(hours=24)
    integration.save()


def demo_queries():
    """Demonstrate various database queries"""
    print("\n=== Database Query Examples ===\n")
    
    # Get all active integrations
    active_integrations = GoHighLevelIntegration.objects.filter(is_active=True)
    print(f"Active integrations: {active_integrations.count()}")
    
    # Get integrations with expired tokens
    expired_tokens = GoHighLevelIntegration.objects.filter(
        expires_at__lt=timezone.now()
    )
    print(f"Integrations with expired tokens: {expired_tokens.count()}")
    
    # Get integrations needing refresh
    needs_refresh = GoHighLevelIntegration.objects.filter(
        expires_at__lte=timezone.now() + timedelta(hours=1)
    )
    print(f"Integrations needing refresh: {needs_refresh.count()}")
    
    # Get webhooks by event type
    install_webhooks = GoHighLevelWebhook.objects.filter(event_type='app.installed')
    print(f"Installation webhooks: {install_webhooks.count()}")
    
    # Get unprocessed webhooks
    unprocessed = GoHighLevelWebhook.objects.filter(processed=False)
    print(f"Unprocessed webhooks: {unprocessed.count()}")


def cleanup_demo_data():
    """Clean up demo data"""
    print("\n=== Cleaning Up Demo Data ===\n")
    
    # Delete demo integrations (this will cascade to webhooks)
    demo_integrations = GoHighLevelIntegration.objects.filter(
        location_id__startswith='demo_'
    )
    count = demo_integrations.count()
    demo_integrations.delete()
    
    print(f"Deleted {count} demo integrations and associated webhooks")


def main():
    """Main demo function"""
    print("🚀 GoHighLevel Integration App Demo")
    print("=" * 50)
    
    try:
        # Run demos
        integration = demo_integration_creation()
        webhooks = demo_webhook_creation(integration)
        demo_token_management(integration)
        demo_queries()
        
        print("\n✅ Demo completed successfully!")
        print("\nTo view the data in Django admin:")
        print("1. Run: python manage.py runserver")
        print("2. Visit: http://localhost:8000/admin/")
        print("3. Login with your superuser credentials")
        print("4. Navigate to 'GoHighLevel Integration' section")
        print("5. Test installation: http://localhost:8000/app/install/")
        
        # Ask if user wants to clean up
        response = input("\nDo you want to clean up the demo data? (y/n): ")
        if response.lower() in ['y', 'yes']:
            cleanup_demo_data()
            print("Demo data cleaned up!")
        else:
            print("Demo data preserved. You can view it in the admin panel.")
            
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        print("Make sure you have:")
        print("1. Run migrations: python manage.py migrate")
        print("2. Created superuser: python manage.py createsuperuser")
        print("3. Installed dependencies: pip install -r requirements.txt")


if __name__ == '__main__':
    main()
