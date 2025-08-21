#!/usr/bin/env python
"""
Test script for GoHighLevel cron functions
Run this to test if your cron functions are working properly
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatreach.settings')
django.setup()

from ghl_integration.cron import (
    refresh_expired_tokens, 
    daily_token_health_check, 
    weekly_bulk_refresh
)
from ghl_integration.services import TokenHealthService, TokenRefreshService
from ghl_integration.models import GoHighLevelIntegration


def test_hourly_refresh():
    """Test the hourly token refresh function"""
    print("🔄 Testing Hourly Token Refresh...")
    print("=" * 50)
    
    try:
        result = refresh_expired_tokens()
        print(f"✅ Result: {result}")
        
        if result.get('success'):
            print(f"   📊 Refreshed: {result.get('refreshed_count', 0)}")
            print(f"   ❌ Failed: {result.get('failed_count', 0)}")
        else:
            print(f"   🚨 Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print()


def test_daily_health_check():
    """Test the daily health check function"""
    print("🏥 Testing Daily Health Check...")
    print("=" * 50)
    
    try:
        health = daily_token_health_check()
        print(f"✅ Result: {health}")
        
        if 'error' not in health:
            print(f"   📊 Total Integrations: {health.get('total_integrations', 0)}")
            print(f"   💚 Healthy Tokens: {health.get('healthy_tokens', 0)}")
            print(f"   ⚠️  Expired Tokens: {health.get('expired_tokens', 0)}")
            print(f"   🔄 Needs Refresh: {health.get('needs_refresh', 0)}")
            print(f"   📈 Health Percentage: {health.get('health_percentage', 0)}%")
        else:
            print(f"   🚨 Error: {health.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print()


def test_weekly_bulk_refresh():
    """Test the weekly bulk refresh function"""
    print("📦 Testing Weekly Bulk Refresh...")
    print("=" * 50)
    
    try:
        result = weekly_bulk_refresh()
        print(f"✅ Result: {result}")
        
        if result.get('success'):
            print(f"   📊 Refreshed: {result.get('refreshed_count', 0)}")
            print(f"   ❌ Failed: {result.get('failed_count', 0)}")
        else:
            print(f"   🚨 Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print()


def test_token_health_service():
    """Test the token health service directly"""
    print("🔍 Testing Token Health Service...")
    print("=" * 50)
    
    try:
        # Get health summary
        health = TokenHealthService.get_token_health_summary()
        print(f"✅ Health Summary: {health}")
        
        # Get tokens expiring soon
        expiring_soon = TokenHealthService.get_tokens_expiring_soon(hours=24)
        print(f"✅ Tokens expiring within 24 hours: {expiring_soon.count()}")
        
        if expiring_soon.exists():
            for integration in expiring_soon[:3]:  # Show first 3
                print(f"   📍 {integration.location_name} ({integration.location_id})")
                print(f"      Expires: {integration.expires_at}")
        
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print()


def test_token_refresh_service():
    """Test the token refresh service directly"""
    print("🔄 Testing Token Refresh Service...")
    print("=" * 50)
    
    try:
        # Test bulk refresh
        result = TokenRefreshService.refresh_expired_tokens()
        print(f"✅ Bulk Refresh Result: {result}")
        
        # Check active integrations
        active_integrations = GoHighLevelIntegration.objects.filter(is_active=True)
        print(f"✅ Active Integrations: {active_integrations.count()}")
        
        if active_integrations.exists():
            print("   📋 Integration Details:")
            for integration in active_integrations[:3]:  # Show first 3
                print(f"      - {integration.location_name}")
                print(f"        Token Expired: {integration.is_token_expired}")
                print(f"        Needs Refresh: {integration.needs_refresh}")
                print(f"        Expires At: {integration.expires_at}")
        
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print()


def test_database_connection():
    """Test database connection and models"""
    print("🗄️  Testing Database Connection...")
    print("=" * 50)
    
    try:
        # Test model access
        total_integrations = GoHighLevelIntegration.objects.count()
        print(f"✅ Total Integrations in DB: {total_integrations}")
        
        active_integrations = GoHighLevelIntegration.objects.filter(is_active=True).count()
        print(f"✅ Active Integrations: {active_integrations}")
        
        # Test webhook model
        from ghl_integration.models import GoHighLevelWebhook
        total_webhooks = GoHighLevelWebhook.objects.count()
        print(f"✅ Total Webhooks: {total_webhooks}")
        
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print()


def main():
    """Run all tests"""
    print("🚀 GoHighLevel Cron Functions Test Suite")
    print("=" * 60)
    print()
    
    # Test database connection first
    test_database_connection()
    
    # Test services
    test_token_health_service()
    test_token_refresh_service()
    
    # Test cron functions
    test_hourly_refresh()
    test_daily_health_check()
    test_weekly_bulk_refresh()
    
    print("🎯 All tests completed!")
    print("=" * 60)
    print()
    print("💡 If all tests pass, your cron functions are working correctly!")
    print("💡 For production, use: python manage.py crontab add")


if __name__ == "__main__":
    main()
