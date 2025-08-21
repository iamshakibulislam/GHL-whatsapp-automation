import json
import requests
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
from .models import GoHighLevelIntegration, GoHighLevelWebhook
from .services import TokenRefreshService, TokenHealthService


# GoHighLevel OAuth configuration
GHL_CLIENT_ID = getattr(settings, 'GHL_CLIENT_ID', 'your_client_id_here')
GHL_CLIENT_SECRET = getattr(settings, 'GHL_CLIENT_SECRET', 'your_client_secret_here')
GHL_REDIRECT_URI = getattr(settings, 'GHL_REDIRECT_URI', 'http://localhost:8000/app/callback/')
GHL_AUTH_URL = 'https://marketplace.gohighlevel.com/oauth/chooselocation'
GHL_TOKEN_URL = 'https://services.leadconnectorhq.com/oauth/token'
GHL_API_BASE = 'https://rest.gohighlevel.com/v1/'


def install_app(request):
    """
    Initial installation URL that redirects to GoHighLevel OAuth
    """
    # Generate state parameter for security
    state = request.session.get('ghl_state', 'default_state')
    
    # Build OAuth URL - GoHighLevel will handle location selection
    # The chooselocation endpoint will show the user's locations and let them choose
    oauth_url = (
        f"{GHL_AUTH_URL}?"
        f"response_type=code&"
        f"client_id={GHL_CLIENT_ID}&"
        f"redirect_uri={GHL_REDIRECT_URI}&"
        f"scope=contacts.readonly%20contacts.write%20locations.readonly%20users.readonly&"
        f"state={state}"
    )
    
    print(f"Redirecting to GoHighLevel OAuth for location selection: {oauth_url}")
    return redirect(oauth_url)


def oauth_callback(request):
    """
    Handle OAuth callback from GoHighLevel
    """
    # Get authorization code from callback
    code = request.GET.get('code')
    state = request.GET.get('state')
    location_id = request.GET.get('locationId')  # May or may not be present initially
    
    print(f"OAuth callback received - code: {code[:10] if code else 'None'}..., state: {state}, locationId: {location_id}")
    
    if not code:
        return JsonResponse({
            'error': 'Missing authorization code',
            'code': code
        }, status=400)
    
    try:
        if not location_id:
            # First callback - user authorized but hasn't selected location yet
            # This is normal! GoHighLevel will send the locationId via webhook later
            print("No locationId provided - this is the initial OAuth callback")
            print("This is expected behavior. GoHighLevel will send locationId via webhook.")
            
            # Don't try to exchange token or get user info here
            # Just return a success message and wait for the webhook
            return render(request, 'ghl_integration/success.html', {
                'message': 'App authorization successful!',
                'details': 'GoHighLevel will complete the installation and send location details via webhook.',
                'waiting_for_webhook': True
            })
        
        # Now we have a location_id (either from callback or determined above)
        print(f"Processing integration for location: {location_id}")
        
        # Exchange code for access token with the location_id
        token_data = exchange_code_for_token(code, location_id)
        
        # Get user information
        user_info = get_user_info(token_data['access_token'])
        
        # Get location details
        location_info = get_location_info(token_data['access_token'], location_id)
        
        # Create or update integration record with complete token data
        integration, created = GoHighLevelIntegration.objects.update_or_create(
            location_id=location_id,
            defaults={
                'location_name': location_info.get('name', ''),
                'user_id': user_info.get('id', ''),
                'user_email': user_info.get('email', ''),
                # Complete token storage
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token', ''),
                'refresh_token_id': token_data.get('refreshTokenId', ''),
                'token_type': token_data.get('token_type', 'Bearer'),
                'expires_at': timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600)),
                # Token metadata
                'user_type': token_data.get('userType', ''),
                'scope': token_data.get('scope', ''),
                'is_bulk_installation': token_data.get('isBulkInstallation', False),
                # Company info
                'company_name': location_info.get('companyName', ''),
                'phone': location_info.get('phone', ''),
                'website': location_info.get('website', ''),
            }
        )
        
        print(f"Integration {'created' if created else 'updated'} successfully for location: {location_id}")
        
        # Return success response
        return render(request, 'ghl_integration/success.html', {
            'integration': integration,
            'created': created
        })
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return JsonResponse({
            'error': 'Failed to complete OAuth flow',
            'details': str(e)
        }, status=500)


def exchange_code_for_token(code, location_id=None):
    """
    Exchange authorization code for access token
    According to GoHighLevel docs: https://developers.gohighlevel.com/docs
    """
    data = {
        'client_id': GHL_CLIENT_ID,
        'client_secret': GHL_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': GHL_REDIRECT_URI,
        'user_type': 'Company',  # Required according to docs - can be 'Company' or 'Location'
    }
    
    # Add location_id if provided
    if location_id:
        data['location_id'] = location_id
        print(f"Attempting to exchange code for token with location_id: {location_id}")
    else:
        print("Attempting to exchange code for token without location_id")
    
    try:
        print(f"Token exchange URL: {GHL_TOKEN_URL}")
        print(f"Client ID: {GHL_CLIENT_ID[:10]}...")
        print(f"Redirect URI: {GHL_REDIRECT_URI}")
        print(f"User Type: {data['user_type']}")
        
        response = requests.post(GHL_TOKEN_URL, data=data, timeout=30)
        response.raise_for_status()
        
        token_data = response.json()
        print(f"Token exchange successful: {token_data.get('token_type', 'unknown')} token received")
        print(f"User Type: {token_data.get('userType', 'unknown')}")
        print(f"Company ID: {token_data.get('companyId', 'unknown')}")
        print(f"Refresh Token ID: {token_data.get('refreshTokenId', 'unknown')}")
        print(f"Scope: {token_data.get('scope', 'unknown')}")
        print(f"Bulk Installation: {token_data.get('isBulkInstallation', 'unknown')}")
        if 'locationId' in token_data:
            print(f"Location ID: {token_data.get('locationId', 'unknown')}")
        return token_data
        
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        raise Exception(f"Failed to connect to GoHighLevel token service: {e}")
    except requests.exceptions.Timeout as e:
        print(f"Timeout error: {e}")
        raise Exception(f"Request to GoHighLevel timed out: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        if hasattr(response, 'status_code') and response.status_code == 400:
            print(f"Response content: {response.text}")
            raise Exception(f"Bad request (400) - check OAuth parameters. Response: {response.text}")
        raise Exception(f"Failed to exchange code for token: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise Exception(f"Unexpected error during token exchange: {e}")


def get_location_info(access_token, location_id):
    """
    Get location information from GoHighLevel API
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Version': '2021-07-28'
    }
    
    url = f"{GHL_API_BASE}locations/{location_id}"
    try:
        print(f"Getting location info from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        location_data = response.json()
        print(f"Location info retrieved successfully")
        return location_data
        
    except requests.exceptions.RequestException as e:
        print(f"Failed to get location info: {e}")
        raise Exception(f"Failed to get location information: {e}")


def get_user_info(access_token):
    """
    Get current user information from GoHighLevel API
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Version': '2021-07-28'
    }
    
    url = f"{GHL_API_BASE}users/me"
    try:
        print(f"Getting user info from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        user_data = response.json()
        print(f"User info retrieved successfully")
        return user_data
        
    except requests.exceptions.RequestException as e:
        print(f"Failed to get user info: {e}")
        raise Exception(f"Failed to get user information: {e}")


def get_user_locations(access_token):
    """
    Get user's locations from GoHighLevel API
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Version': '2021-07-28'
    }
    
    url = f"{GHL_API_BASE}locations"
    try:
        print(f"Getting user locations from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        locations_data = response.json()
        print(f"User locations retrieved successfully")
        return locations_data
        
    except requests.exceptions.RequestException as e:
        print(f"Failed to get user locations: {e}")
        raise Exception(f"Failed to get user locations: {e}")


def refresh_token(request, integration_id):
    """
    Refresh access token using refresh token
    """
    try:
        integration = GoHighLevelIntegration.objects.get(id=integration_id)
        
        if not integration.refresh_token:
            return JsonResponse({'error': 'No refresh token available'}, status=400)
        
        data = {
            'client_id': GHL_CLIENT_ID,
            'client_secret': GHL_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': integration.refresh_token,
            'user_type': 'Company'  # Required according to docs
        }
        
        response = requests.post(GHL_TOKEN_URL, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Update integration with new tokens and metadata
        integration.access_token = token_data['access_token']
        integration.refresh_token = token_data.get('refresh_token', integration.refresh_token)
        integration.refresh_token_id = token_data.get('refreshTokenId', integration.refresh_token_id)
        integration.expires_at = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
        integration.user_type = token_data.get('userType', integration.user_type)
        integration.scope = token_data.get('scope', integration.scope)
        integration.is_bulk_installation = token_data.get('isBulkInstallation', integration.is_bulk_installation)
        integration.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Token refreshed successfully',
            'expires_at': integration.expires_at.isoformat()
        })
        
    except GoHighLevelIntegration.DoesNotExist:
        return JsonResponse({'error': 'Integration not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Failed to refresh token: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_handler(request):
    """
    Handle webhooks from GoHighLevel
    """
    try:
        # Parse webhook data
        webhook_data = json.loads(request.body)
        
        # Extract location ID from webhook - according to official GoHighLevel docs
        # Docs show: "type": "INSTALL", "locationId": "HjiMUOsCCHCjtxzEf8PR"
        location_id = (
            webhook_data.get('locationId') or  # Primary field from docs
            webhook_data.get('location_id') or 
            webhook_data.get('location', {}).get('id') or
            webhook_data.get('data', {}).get('locationId')
        )
        
        # Extract event type - docs show "type": "INSTALL"
        event_type = (
            webhook_data.get('type') or  # Primary field from docs
            webhook_data.get('eventType') or
            'unknown'
        )
        
        print(f"Webhook received - Type: {event_type}, Location ID: {location_id}")
        print(f"Full webhook payload: {webhook_data}")
        
        if not location_id:
            return JsonResponse({
                'error': 'Missing locationId', 
                'webhook_data': webhook_data,
                'note': 'According to GoHighLevel docs, webhook should include locationId field'
            }, status=400)
        
        # Find corresponding integration
        try:
            integration = GoHighLevelIntegration.objects.get(location_id=location_id)
        except GoHighLevelIntegration.DoesNotExist:
            # If integration doesn't exist, this might be the initial install webhook
            # We should create the integration here
            print(f"Integration not found for location {location_id}, creating new one from webhook")
            
            # Extract company and user info from webhook
            company_id = webhook_data.get('companyId')
            user_id = webhook_data.get('userId')
            company_name = webhook_data.get('companyName')
            
            # Create integration from webhook data
            # Note: We need to provide required fields with defaults
            integration = GoHighLevelIntegration.objects.create(
                location_id=location_id,
                company_id=company_id or '',
                user_id=user_id or '',
                company_name=company_name or '',
                location_name=webhook_data.get('locationName', ''),
                # Required fields with defaults
                access_token='',  # Will be updated later via OAuth
                refresh_token='',  # Will be updated later via OAuth
                refresh_token_id='',  # Will be updated later via OAuth
                token_type='Bearer',  # Default token type
                expires_at=timezone.now() + timedelta(hours=1),  # Default expiration
                user_type='',  # Will be updated later via OAuth
                scope='',  # Will be updated later via OAuth
                is_bulk_installation=False,  # Default value
                is_active=True
            )
            print(f"Created new integration from webhook: {integration.id}")
        
        try:
            # Store webhook event
            webhook = GoHighLevelWebhook.objects.create(
                integration=integration,
                event_type=event_type,
                event_data=webhook_data
            )
            
            print(f"Webhook stored successfully: {webhook.id}")
            
            # Process webhook based on event type
            process_webhook(webhook)
            
            return JsonResponse({'success': True, 'webhook_id': str(webhook.id)})
            
        except Exception as e:
            print(f"Error storing/processing webhook: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'error': 'Webhook processing failed',
                'details': str(e)
            }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Webhook processing failed: {str(e)}'}, status=500)


def process_webhook(webhook):
    """
    Process webhook events based on type
    According to official GoHighLevel docs
    """
    event_type = webhook.event_type
    
    print(f"Processing webhook event: {event_type}")
    
    if event_type == 'UNINSTALL':
        # Handle app uninstallation - docs show "type": "UNINSTALL"
        print(f"Processing app uninstall for location: {webhook.integration.location_id}")
        webhook.integration.is_active = False
        webhook.integration.save()
    
    elif event_type == 'INSTALL':
        # Handle app installation - docs show "type": "INSTALL"
        print(f"Processing app install for location: {webhook.integration.location_id}")
        webhook.integration.is_active = True
        webhook.integration.save()
        
        # Update integration with webhook data if available
        webhook_data = webhook.event_data
        if webhook_data.get('companyName'):
            webhook.integration.company_name = webhook_data['companyName']
        if webhook_data.get('companyId'):
            webhook.integration.company_id = webhook_data['companyId']
        if webhook_data.get('userId'):
            webhook.integration.user_id = webhook_data['userId']
        webhook.integration.save()
    
    else:
        print(f"Unknown webhook event type: {event_type}")
    
    # Mark webhook as processed
    webhook.processed = True
    webhook.save()
    print(f"Webhook {webhook.id} processed successfully")


def integration_status(request, integration_id):
    """
    Get integration status and token information
    """
    try:
        integration = GoHighLevelIntegration.objects.get(id=integration_id)
        
        return JsonResponse({
            'id': str(integration.id),
            'location_id': integration.location_id,
            'location_name': integration.location_name,
            'user_email': integration.user_email,
            'is_active': integration.is_active,
            'is_token_expired': integration.is_token_expired,
            'needs_refresh': integration.needs_refresh,
            'expires_at': integration.expires_at.isoformat(),
            'installed_at': integration.installed_at.isoformat(),
            'last_used_at': integration.last_used_at.isoformat()
        })
        
    except GoHighLevelIntegration.DoesNotExist:
        return JsonResponse({'error': 'Integration not found'}, status=404)


def list_integrations(request):
    """
    List all GoHighLevel integrations
    """
    integrations = GoHighLevelIntegration.objects.all()
    
    integrations_data = []
    for integration in integrations:
        integrations_data.append({
            'id': str(integration.id),
            'location_id': integration.location_id,
            'location_name': integration.location_name,
            'user_email': integration.user_email,
            'is_active': integration.is_active,
            'is_token_expired': integration.is_token_expired,
            'installed_at': integration.installed_at.isoformat()
        })
    
    return JsonResponse({'integrations': integrations_data})


def test_connectivity(request):
    """
    Test connectivity to GoHighLevel services for debugging
    """
    results = {}
    
    # Test OAuth URL
    try:
        import requests
        response = requests.get(GHL_AUTH_URL, timeout=10)
        results['oauth_url'] = {
            'status': 'success',
            'status_code': response.status_code,
            'url': GHL_AUTH_URL
        }
    except Exception as e:
        results['oauth_url'] = {
            'status': 'error',
            'error': str(e),
            'url': GHL_AUTH_URL
        }
    
    # Test Token URL (HEAD request to check if reachable)
    try:
        response = requests.head(GHL_TOKEN_URL, timeout=10)
        results['token_url'] = {
            'status': 'success',
            'status_code': response.status_code,
            'url': GHL_TOKEN_URL
        }
    except Exception as e:
        results['token_url'] = {
            'status': 'error',
            'error': str(e),
            'url': GHL_TOKEN_URL
        }
    
    # Test API Base
    try:
        response = requests.head(GHL_API_BASE, timeout=10)
        results['api_base'] = {
            'status': 'success',
            'status_code': response.status_code,
            'url': GHL_API_BASE
        }
    except Exception as e:
        results['api_base'] = {
            'status': 'error',
            'error': str(e),
            'url': GHL_API_BASE
        }
    
    # Add configuration info
    results['config'] = {
        'client_id': GHL_CLIENT_ID[:10] + '...' if len(GHL_CLIENT_ID) > 10 else GHL_CLIENT_ID,
        'redirect_uri': GHL_REDIRECT_URI,
        'auth_url': GHL_AUTH_URL,
        'token_url': GHL_TOKEN_URL,
        'api_base': GHL_API_BASE
    }
    
    return JsonResponse(results)


def token_health_summary(request):
    """
    Get overall token health summary for all integrations
    """
    try:
        health_data = TokenHealthService.get_token_health_summary()
        return JsonResponse(health_data)
    except Exception as e:
        return JsonResponse({
            'error': 'Failed to get token health summary',
            'details': str(e)
        }, status=500)


def bulk_token_refresh(request):
    """
    Manually trigger bulk token refresh for all integrations
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        result = TokenRefreshService.refresh_expired_tokens()
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({
            'error': 'Failed to perform bulk token refresh',
            'details': str(e)
        }, status=500)


def get_valid_token(request, integration_id):
    """
    Get a valid access token for an integration, refreshing if necessary
    """
    try:
        integration = GoHighLevelIntegration.objects.get(id=integration_id)
        
        if not integration.is_active:
            return JsonResponse({
                'error': 'Integration is not active'
            }, status=500)
        
        # Get valid token (will refresh if needed)
        token, was_refreshed = TokenRefreshService.get_valid_token(integration)
        
        return JsonResponse({
            'access_token': token,
            'was_refreshed': was_refreshed,
            'expires_at': integration.expires_at.isoformat(),
            'needs_refresh': integration.needs_refresh,
            'is_expired': integration.is_token_expired
        })
        
    except GoHighLevelIntegration.DoesNotExist:
        return JsonResponse({'error': 'Integration not found'}, status=404)
    except Exception as e:
        return JsonResponse({
            'error': 'Failed to get valid token',
            'details': str(e)
        }, status=500)
