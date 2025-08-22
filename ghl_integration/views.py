import json
import requests
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.db import transaction
from .models import GoHighLevelIntegration, GoHighLevelWebhook, WhatsAppAccessToken
from .services import TokenRefreshService, TokenHealthService, GoHighLevelDecryptionService
import logging
import base64

logger = logging.getLogger(__name__)


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
        
        # Deactivate the integration
        webhook.integration.is_active = False
        webhook.integration.save()
        
        # Delete associated WhatsApp access tokens
        try:
            whatsapp_tokens = WhatsAppAccessToken.objects.filter(integration=webhook.integration)
            deleted_count = whatsapp_tokens.count()
            
            if deleted_count > 0:
                print(f"🗑️ Deleting {deleted_count} WhatsApp access token(s) for uninstalled location")
                whatsapp_tokens.delete()
                print(f"✅ Successfully deleted {deleted_count} WhatsApp access token(s)")
            else:
                print(f"ℹ️ No WhatsApp access tokens found for location {webhook.integration.location_id}")
                
        except Exception as e:
            print(f"⚠️ Warning: Could not delete WhatsApp access tokens: {str(e)}")
        
        print(f"✅ App uninstall processed successfully for location: {webhook.integration.location_id}")
    
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
        
        print(f"✅ App install processed successfully for location: {webhook.integration.location_id}")
    
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
    try:
        # Test basic connectivity
        import requests
        
        test_urls = [
            'https://services.leadconnectorhq.com/oauth/token',
            'https://services.leadconnectorhq.com/oauth/authorize',
            'https://rest.gohighlevel.com/v1/'
        ]
        
        results = {}
        for url in test_urls:
            try:
                response = requests.get(url, timeout=10)
                results[url] = {
                    'status_code': response.status_code,
                    'accessible': response.status_code < 400
                }
            except Exception as e:
                results[url] = {
                    'status_code': None,
                    'accessible': False,
                    'error': str(e)
                }
        
        return JsonResponse({
            'success': True,
            'connectivity_test': results,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST", "DELETE", "OPTIONS"])
def manage_whatsapp_token(request):
    """
    API endpoint to manage WhatsApp access tokens
    """
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
        
    if request.method == 'GET':
        # Get token for a specific location
        location_id = request.GET.get('location_id')
        if not location_id:
            return JsonResponse({
                'error': 'location_id parameter is required'
            }, status=400)
        
        try:
            integration = GoHighLevelIntegration.objects.get(location_id=location_id)
            try:
                token = WhatsAppAccessToken.objects.get(integration=integration)
                return JsonResponse({
                    'success': True,
                    'token': {
                        'id': str(token.id),
                        'access_token': token.access_token[:20] + '...' if len(token.access_token) > 20 else token.access_token,
                        'created_at': token.created_at.isoformat(),
                        'updated_at': token.updated_at.isoformat()
                    }
                })
            except WhatsAppAccessToken.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'No WhatsApp access token found for this location'
                }, status=404)
                
        except GoHighLevelIntegration.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'No GoHighLevel integration found for this location'
            }, status=404)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            location_id = data.get('location_id')
            access_token = data.get('access_token')
            
            if not all([location_id, access_token]):
                return JsonResponse({
                    'error': 'location_id and access_token are required'
                }, status=400)
            
            # Check if integration exists
            try:
                integration = GoHighLevelIntegration.objects.get(location_id=location_id)
            except GoHighLevelIntegration.DoesNotExist:
                return JsonResponse({
                    'error': 'No GoHighLevel integration found for this location'
                }, status=404)
            
            # Check if token already exists
            token, created = WhatsAppAccessToken.objects.get_or_create(
                integration=integration,
                defaults={
                    'access_token': access_token
                }
            )
            
            if not created:
                # Update existing token
                token.access_token = access_token
            
            token.save()
            
            action = 'created' if created else 'updated'
            return JsonResponse({
                'success': True,
                'message': f'WhatsApp access token {action} successfully',
                'token_id': str(token.id),
                'action': action
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Failed to manage token: {str(e)}'
            }, status=500)
    
    elif request.method == 'DELETE':
        # Delete token
        location_id = request.GET.get('location_id')
        if not location_id:
            return JsonResponse({
                'error': 'location_id parameter is required'
            }, status=400)
        
        try:
            integration = GoHighLevelIntegration.objects.get(location_id=location_id)
            try:
                token = WhatsAppAccessToken.objects.get(integration=integration)
                token.delete()
                return JsonResponse({
                    'success': True,
                    'message': 'WhatsApp access token deleted successfully'
                })
            except WhatsAppAccessToken.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'No WhatsApp access token found for this location'
                }, status=404)
                
        except GoHighLevelIntegration.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'No GoHighLevel integration found for this location'
            }, status=404)
    
    else:
        return JsonResponse({
            'error': 'Method not allowed'
        }, status=405)


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


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def user_identification(request):
    """
    Handle user identification requests from the frontend
    """
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    try:
        # Parse the request body
        body = request.body.decode('utf-8')
        data = json.loads(body) if body else {}
        
        # Extract context data
        context = data.get('context', {})
        
        # Initialize user data
        user_data = {
            'location_id': None,
            'user_id': None,
            'company_id': None,
            'user_email': None,
            'detection_methods': []
        }

        # Check for encrypted postMessage data
        if context.get('encrypted_user_data'):
            encrypted_data = context.get('encrypted_user_data')
            
            # Check if data is already decrypted by frontend
            if context.get('decryption_successful') and context.get('decrypted_user_data'):
                # Frontend already decrypted the data
                decrypted_data = context.get('decrypted_user_data')
                
                # Extract comprehensive user data
                user_data.update({
                    'location_id': decrypted_data.get('activeLocation') or decrypted_data.get('locationId') or decrypted_data.get('companyId'),
                    'user_id': decrypted_data.get('userId') or decrypted_data.get('id'),
                    'company_id': decrypted_data.get('companyId'),
                    'user_email': decrypted_data.get('email'),
                    'user_name': decrypted_data.get('userName') or decrypted_data.get('name') or decrypted_data.get('firstName') or decrypted_data.get('lastName') or decrypted_data.get('fullName'),
                    'user_role': decrypted_data.get('role'),
                    'location_name': decrypted_data.get('locationName'),
                    'company_name': decrypted_data.get('companyName'),
                    'detection_methods': ['PostMessage + Frontend Decryption']
                })
                
                print(f"🔍 RAW DECRYPTED DATA DEBUG:")
                for key, value in decrypted_data.items():
                    print(f"   {key}: {value}")
                
                print(f"✅ User data received (frontend decrypted):")
                print(f"   User ID: {user_data['user_id']}")
                print(f"   Email: {user_data['user_email']}")
                print(f"   Company ID: {user_data['company_id']}")
                print(f"   Location ID: {user_data['location_id']}")
                print(f"   User Name: {user_data['user_name']}")
                print(f"   User Role: {user_data['user_role']}")
                print(f"   Location Name: {user_data['location_name']}")
                print(f"   Company Name: {user_data['company_name']}")
                print(f"   Raw encrypted data: {encrypted_data[:100]}...")
                
                # Create comprehensive session for this user
                request.session['ghl_user_data'] = {
                    # Core identification
                    'user_id': user_data['user_id'],
                    'user_email': user_data['user_email'],
                    'user_name': user_data['user_name'],
                    'user_role': user_data['user_role'],
                    
                    # GoHighLevel context
                    'company_id': user_data['company_id'],
                    'company_name': user_data['company_name'],
                    'location_id': user_data['location_id'],
                    'location_name': user_data['location_name'],
                    
                    # Additional context from decrypted data
                    'ghl_context': {
                        'raw_decrypted_data': decrypted_data,
                        'encrypted_data_sample': encrypted_data[:100] + '...' if len(encrypted_data) > 100 else encrypted_data
                    },
                    
                    # Session metadata
                    'detection_methods': user_data['detection_methods'],
                    'session_created': timezone.now().isoformat(),
                    'last_activity': timezone.now().isoformat(),
                    'session_version': '2.0'  # Track session format version
                }
                
                # Set session expiry (24 hours)
                request.session.set_expiry(86400)
                
                print(f"✅ Comprehensive user session created:")
                print(f"   Session ID: {request.session.session_key}")
                print(f"   User ID: {user_data['user_id']}")
                print(f"   Company ID: {user_data['company_id']}")
                print(f"   Location ID: {user_data['location_id']}")
                print(f"   Session expires in: 24 hours")
                print(f"   Stored fields: {list(request.session['ghl_user_data'].keys())}")
                
            else:
                # Attempt to decrypt the data in backend
                try:
                    decrypted_data = GoHighLevelDecryptionService.decrypt_user_data(encrypted_data)
                    if decrypted_data:
                        # Use decrypted data for user identification
                        user_data.update({
                            'location_id': decrypted_data.get('activeLocation') or decrypted_data.get('companyId'),
                            'user_id': decrypted_data.get('userId') or decrypted_data.get('id'),
                            'company_id': decrypted_data.get('companyId'),
                            'user_email': decrypted_data.get('email'),
                            'user_name': decrypted_data.get('userName') or decrypted_data.get('name') or decrypted_data.get('firstName') or decrypted_data.get('lastName') or decrypted_data.get('fullName'),
                            'user_role': decrypted_data.get('role'),
                            'location_name': decrypted_data.get('locationName'),
                            'company_name': decrypted_data.get('companyName'),
                            'detection_methods': ['PostMessage + Backend Decryption']
                        })
                        
                        print(f"✅ User identified via backend decryption:")
                        print(f"   User ID: {user_data['user_id']}")
                        print(f"   Email: {user_data['user_email']}")
                        print(f"   Company ID: {user_data['company_id']}")
                        print(f"   Location ID: {user_data['location_id']}")
                        print(f"   User Name: {user_data['user_name']}")
                        print(f"   User Role: {user_data['user_role']}")
                        print(f"   Location Name: {user_data['location_name']}")
                        print(f"   Company Name: {user_data['company_name']}")
                        
                        # Create comprehensive session for this user
                        request.session['ghl_user_data'] = {
                            # Core identification
                            'user_id': user_data['user_id'],
                            'user_email': user_data['user_email'],
                            'user_name': user_data['user_name'],
                            'user_role': user_data['user_role'],
                            
                            # GoHighLevel context
                            'company_id': user_data['company_id'],
                            'company_name': user_data['company_name'],
                            'location_id': user_data['location_id'],
                            'location_name': user_data['location_name'],
                            
                            # Additional context from decrypted data
                            'ghl_context': {
                                'raw_decrypted_data': decrypted_data,
                                'encrypted_data_sample': 'Backend decrypted'
                            },
                            
                            # Session metadata
                            'detection_methods': user_data['detection_methods'],
                            'session_created': timezone.now().isoformat(),
                            'last_activity': timezone.now().isoformat(),
                            'session_version': '2.0'  # Track session format version
                        }
                        
                        # Set session expiry (24 hours)
                        request.session.set_expiry(86400)
                        
                        print(f"✅ Comprehensive user session created (backend):")
                        print(f"   Session ID: {request.session.session_key}")
                        print(f"   User ID: {user_data['user_id']}")
                        print(f"   Company ID: {user_data['company_id']}")
                        print(f"   Location ID: {user_data['location_id']}")
                        print(f"   Session expires in: 24 hours")
                        print(f"   Stored fields: {list(request.session['ghl_user_data'].keys())}")
                        
                    else:
                        print("❌ Backend decryption failed")
                        
                except Exception as e:
                    print(f"❌ Backend decryption error: {str(e)}")

        # Check for other detection methods
        if not user_data['user_id']:
            # Try URL parameters
            location_id = request.GET.get('locationId') or request.GET.get('location_id')
            user_id = request.GET.get('userId') or request.GET.get('user_id')
            company_id = request.GET.get('companyId') or request.GET.get('company_id')
            
            if location_id or user_id or company_id:
                user_data.update({
                    'location_id': location_id,
                    'user_id': user_id,
                    'company_id': company_id,
                    'user_email': request.GET.get('userEmail') or request.GET.get('email'),
                    'user_name': request.GET.get('userName') or request.GET.get('name'),
                    'user_role': request.GET.get('userRole') or request.GET.get('role'),
                    'location_name': request.GET.get('locationName'),
                    'company_name': request.GET.get('companyName'),
                    'detection_methods': ['URL Parameters']
                })
                print(f"✅ User identified via URL parameters:")
                print(f"   Location ID: {location_id}")
                print(f"   User ID: {user_id}")
                print(f"   Company ID: {company_id}")
                print(f"   User Email: {user_data['user_email']}")
                print(f"   User Name: {user_data['user_name']}")
                print(f"   User Role: {user_data['user_role']}")
                print(f"   Location Name: {user_data['location_name']}")
                print(f"   Company Name: {user_data['company_name']}")
                
                # Create comprehensive session for this user
                request.session['ghl_user_data'] = {
                    # Core identification
                    'user_id': user_id,
                    'user_email': user_data['user_email'],
                    'user_name': user_data['user_name'],
                    'user_role': user_data['user_role'],
                    
                    # GoHighLevel context
                    'company_id': company_id,
                    'company_name': user_data['company_name'],
                    'location_id': location_id,
                    'location_name': user_data['location_name'],
                    
                    # Additional context from URL parameters
                    'ghl_context': {
                        'raw_url_params': dict(request.GET),
                        'detection_method': 'URL Parameters'
                    },
                    
                    # Session metadata
                    'detection_methods': user_data['detection_methods'],
                    'session_created': timezone.now().isoformat(),
                    'last_activity': timezone.now().isoformat(),
                    'session_version': '2.0'  # Track session format version
                }
                request.session.set_expiry(86400)
                
                print(f"✅ Comprehensive user session created (URL params):")
                print(f"   Session ID: {request.session.session_key}")
                print(f"   User ID: {user_id}")
                print(f"   Company ID: {company_id}")
                print(f"   Location ID: {location_id}")
                print(f"   Session expires in: 24 hours")
                print(f"   Stored fields: {list(request.session['ghl_user_data'].keys())}")

        # Check for HTTP headers
        if not user_data['user_id']:
            referer = request.META.get('HTTP_REFERER', '')
            origin = request.META.get('HTTP_ORIGIN', '')
            
            if referer or origin:
                user_data['detection_methods'].append('HTTP Headers')
                print(f"📋 HTTP Headers:")
                print(f"   Referer: {referer}")
                print(f"   Origin: {origin}")

        # Final user data summary
        print(f"\n🎯 FINAL USER DATA:")
        print(f"   Location ID: {user_data['location_id']}")
        print(f"   User ID: {user_data['user_id']}")
        print(f"   Company ID: {user_data['company_id']}")
        print(f"   Email: {user_data['user_email']}")
        print(f"   Detection Methods: {', '.join(user_data['detection_methods'])}")

        # Return the user data
        return JsonResponse({
            'success': True,
            'user_data': user_data,
            'timestamp': timezone.now().isoformat()
        })

    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def app_landing(request):
    """
    Main app landing page that appears when users click on the app in GHL sidebar
    """
    try:
        # SERVER-SIDE REFERER TRACKING
        print("=== SERVER-SIDE REFERER ANALYSIS ===")
        
        # Get referer from HTTP headers
        referer = request.META.get('HTTP_REFERER', '')
        print(f"HTTP_REFERER: {referer}")
        
        # Get all HTTP headers for debugging
        all_headers = {k: v for k, v in request.META.items() if k.startswith('HTTP_')}
        print(f"All HTTP headers: {all_headers}")
        
        # Get additional request information
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        host = request.META.get('HTTP_HOST', '')
        origin = request.META.get('HTTP_ORIGIN', '')
        sec_fetch_dest = request.META.get('HTTP_SEC_FETCH_DEST', '')
        sec_fetch_site = request.META.get('HTTP_SEC_FETCH_SITE', '')
        
        print(f"User Agent: {user_agent}")
        print(f"Host: {host}")
        print(f"Origin: {origin}")
        print(f"Sec-Fetch-Dest: {sec_fetch_dest}")
        print(f"Sec-Fetch-Site: {sec_fetch_site}")
        
        # Analyze referer if available
        referer_analysis = {}
        if referer:
            try:
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(referer)
                
                referer_analysis = {
                    'scheme': parsed_url.scheme,
                    'hostname': parsed_url.hostname,
                    'path': parsed_url.path,
                    'query_params': parse_qs(parsed_url.query),
                    'fragment': parsed_url.fragment,
                    'is_ghl': any(domain in parsed_url.hostname.lower() for domain in ['gohighlevel.com', 'leadconnectorhq.com'])
                }
                
                print(f"Referer Analysis: {referer_analysis}")
                
                # Extract potential user context from referer
                if referer_analysis['is_ghl']:
                    print("✅ Referer is from GoHighLevel!")
                    
                    # Extract IDs from path
                    path_parts = parsed_url.path.strip('/').split('/')
                    print(f"Path parts: {path_parts}")
                    
                    # Look for ID patterns in path
                    for i, part in enumerate(path_parts):
                        if part in ['location', 'contact', 'user', 'company', 'funnel', 'page', 'campaign']:
                            if i + 1 < len(path_parts):
                                id_value = path_parts[i + 1]
                                print(f"✅ Found {part} ID: {id_value}")
                                referer_analysis[f'{part}_id'] = id_value
                    
                    # Extract IDs from query parameters
                    for key, values in referer_analysis['query_params'].items():
                        if any(id_type in key.lower() for id_type in ['id', 'location', 'user', 'company', 'contact']):
                            print(f"✅ Found query param {key}: {values[0]}")
                            referer_analysis[f'query_{key}'] = values[0]
                            
            except Exception as e:
                print(f"⚠️ Error parsing referer: {e}")
                referer_analysis = {'error': str(e)}
        else:
            print("❌ No referer header found")
            
            # Check if this might be an iframe request
            if sec_fetch_dest == 'iframe':
                print("✅ Detected iframe request (Sec-Fetch-Dest: iframe)")
                referer_analysis['iframe_request'] = True
                
            if sec_fetch_site == 'cross-site':
                print("✅ Detected cross-site request (Sec-Fetch-Site: cross-site)")
                referer_analysis['cross_site'] = True
                
            if origin:
                print(f"✅ Found Origin header: {origin}")
                referer_analysis['origin'] = origin
                
                # Check if origin is from GoHighLevel
                if any(domain in origin.lower() for domain in ['gohighlevel.com', 'leadconnectorhq.com']):
                    print("✅ Origin is from GoHighLevel!")
                    referer_analysis['origin_is_ghl'] = True
        
        print("=====================================")
        
        # Get ALL possible user identification parameters from GoHighLevel
        location_id = request.GET.get('locationId')
        user_id = request.GET.get('userId')
        company_id = request.GET.get('companyId')
        contact_id = request.GET.get('contactId')
        funnel_id = request.GET.get('funnelId')
        page_id = request.GET.get('pageId')
        campaign_id = request.GET.get('campaignId')
        
        # Get referer and user agent for additional context
        referer = request.META.get('HTTP_REFERER', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Log all parameters for debugging
        print(f"=== GoHighLevel App Landing Request ===")
        print(f"Location ID: {location_id}")
        print(f"User ID: {user_id}")
        print(f"Company ID: {company_id}")
        print(f"Contact ID: {contact_id}")
        print(f"Funnel ID: {funnel_id}")
        print(f"Page ID: {page_id}")
        print(f"Campaign ID: {campaign_id}")
        print(f"Referer: {referer}")
        print(f"User Agent: {user_agent}")
        print(f"All GET params: {dict(request.GET)}")
        print(f"All headers: {dict(request.META)}")
        print(f"=====================================")
        
        # Combine server-side and client-side detection
        context = {
            'location_id': location_id,
            'user_id': user_id,
            'company_id': company_id,
            'contact_id': contact_id,
            'funnel_id': funnel_id,
            'page_id': page_id,
            'campaign_id': campaign_id,
            'referer': referer,
            'user_agent': user_agent,
            'all_params': dict(request.GET),
            'has_integration': False,
            'integration': None,
            # Server-side referer analysis
            'server_referer_analysis': referer_analysis,
            'http_headers': all_headers,
            'is_iframe_request': sec_fetch_dest == 'iframe',
            'is_cross_site': sec_fetch_site == 'cross-site',
            'origin_header': origin,
        }
        
        # Try to extract location ID from server-side analysis if not in GET params
        if not location_id and referer_analysis.get('location_id'):
            location_id = referer_analysis['location_id']
            context['location_id'] = location_id
            print(f"✅ Extracted location ID from referer: {location_id}")
            
        if not location_id and referer_analysis.get('query_locationId'):
            location_id = referer_analysis['query_locationId']
            context['location_id'] = location_id
            print(f"✅ Extracted location ID from referer query: {location_id}")
        
        if location_id:
            # Check if we have an integration for this location
            try:
                integration = GoHighLevelIntegration.objects.get(
                    location_id=location_id,
                    is_active=True
                )
                context['has_integration'] = True
                context['integration'] = integration
                
                # Check token status
                context['token_status'] = {
                    'is_expired': integration.is_token_expired,
                    'needs_refresh': integration.needs_refresh,
                    'expires_at': integration.expires_at,
                    'last_used': integration.last_used_at,
                }
                
                # Update last used timestamp
                integration.last_used_at = timezone.now()
                integration.save()
                
                print(f"✅ Integration found for location: {location_id}")
                print(f"   Company: {integration.company_name}")
                print(f"   User: {integration.user_email}")
                
            except GoHighLevelIntegration.DoesNotExist:
                # No integration found - user needs to install
                context['needs_installation'] = True
                print(f"❌ No integration found for location: {location_id}")
        else:
            # No location ID - show installation instructions
            context['needs_installation'] = True
            print(f"⚠️ No location ID provided")
            
        # Set response headers for iframe embedding
        response = render(request, 'ghl_integration/app_landing.html', context)
        response['X-Frame-Options'] = 'ALLOWALL'  # Allow embedding in iframes
        response['Access-Control-Allow-Origin'] = '*'  # Allow cross-origin requests
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Prevent caching
        
        return response
        
    except Exception as e:
        logger.error(f"Error in app landing page: {str(e)}")
        print(f"❌ Error in app landing: {str(e)}")
        return render(request, 'ghl_integration/error.html', {
            'error_message': 'Unable to load app. Please try again.'
        })


def app_manifest(request):
    """
    Generate and serve the GoHighLevel app manifest
    """
    manifest = {
        "name": "WhatReach",
        "description": "Advanced lead management and automation platform",
        "version": "1.0.0",
        "type": "private",
        "author": "WhatReach Team",
        "website": "https://814e0c0adec4.ngrok-free.app",
        "icon": "https://814e0c0adec4.ngrok-free.app/static/ghl_integration/icon.svg",
        "permissions": [
            "contacts.read",
            "contacts.write", 
            "locations.read",
            "users.read",
            "sidebar.access",
            "navigation.access"
        ],
        "sidebar_integration": {
            "type": "iframe",
            "url": "https://814e0c0adec4.ngrok-free.app/app/ghl-integration/",
            "resizable": True,
            "min_width": 400,
            "min_height": 600,
            "position": "right",
            "order": 1,
            "show_in_navigation": True,
            "show_in_sidebar": True,
            "show_in_header": False,
            "show_in_footer": False
        },
        "post_install_redirect": "https://814e0c0adec4.ngrok-free.app/app/ghl-integration/"
    }
    
    response = JsonResponse(manifest)
    response['Content-Type'] = 'application/json'
    response['Access-Control-Allow-Origin'] = '*'
    return response


def sidebar_integration(request):
    """
    Sidebar integration view - called by GoHighLevel to embed app in sidebar
    """
    try:
        # Get the location_id from the request (GHL sends this)
        location_id = request.GET.get('locationId')
        user_id = request.GET.get('userId')
        company_id = request.GET.get('companyId')
        
        context = {
            'location_id': location_id,
            'user_id': user_id,
            'company_id': company_id,
            'is_sidebar': True,  # Flag to indicate this is sidebar view
            'has_integration': False,
            'integration': None,
        }
        
        if location_id:
            # Check if we have an integration for this location
            try:
                integration = GoHighLevelIntegration.objects.get(
                    location_id=location_id,
                    is_active=True
                )
                context['has_integration'] = True
                context['integration'] = integration
                
                # Check token status
                context['token_status'] = {
                    'is_expired': integration.is_token_expired,
                    'needs_refresh': integration.needs_refresh,
                    'expires_at': integration.expires_at,
                    'last_used': integration.last_used_at,
                }
                
            except GoHighLevelIntegration.DoesNotExist:
                # No integration found - user needs to install
                context['needs_installation'] = True
        else:
            # No location ID - show installation instructions
            context['needs_installation'] = True
            
        # Set response headers for sidebar integration
        response = render(request, 'ghl_integration/sidebar.html', context)
        response['X-Frame-Options'] = 'ALLOWALL'  # Allow embedding in iframes
        response['Access-Control-Allow-Origin'] = '*'  # Allow cross-origin requests
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Prevent caching
        
        return response
        
    except Exception as e:
        logger.error(f"Error in sidebar integration: {str(e)}")
        return render(request, 'ghl_integration/error.html', {
            'error_message': 'Unable to load sidebar integration. Please try again.'
        })


def sidebar_widget(request):
    """
    Sidebar widget view for adding to GoHighLevel custom sidebar widgets
    """
    try:
        # Get the location_id from the request (GHL sends this)
        location_id = request.GET.get('locationId')
        user_id = request.GET.get('userId')
        company_id = request.GET.get('companyId')
        
        context = {
            'location_id': location_id,
            'user_id': user_id,
            'company_id': company_id,
            'is_sidebar_widget': True,  # Flag to indicate this is sidebar widget
            'has_integration': False,
            'integration': None,
        }
        
        if location_id:
            # Check if we have an integration for this location
            try:
                integration = GoHighLevelIntegration.objects.get(
                    location_id=location_id,
                    is_active=True
                )
                context['has_integration'] = True
                context['integration'] = integration
                
                # Check token status
                context['token_status'] = {
                    'is_expired': integration.is_token_expired,
                    'needs_refresh': integration.needs_refresh,
                    'expires_at': integration.expires_at,
                    'last_used': integration.last_used_at,
                }
                
            except GoHighLevelIntegration.DoesNotExist:
                # No integration found - user needs to install
                context['needs_installation'] = True
        else:
            # No location ID - show installation instructions
            context['needs_installation'] = True
            
        # Set response headers for widget embedding
        response = render(request, 'ghl_integration/sidebar_widget.html', context)
        response['X-Frame-Options'] = 'ALLOWALL'  # Allow embedding in iframes
        response['Access-Control-Allow-Origin'] = '*'  # Allow cross-origin requests
        
        return response
        
    except Exception as e:
        logger.error(f"Error in sidebar widget: {str(e)}")
        return render(request, 'ghl_integration/error.html', {
            'error_message': 'Unable to load sidebar widget. Please try again.'
        })


def test_iframe(request):
    """Test iframe embedding"""
    return render(request, 'ghl_integration/test_iframe.html')

def postmessage_test(request):
    """Test postMessage communication with GoHighLevel"""
    return render(request, 'ghl_integration/postmessage_test.html')

def require_ghl_session(view_func):
    """Decorator to check if user has a valid GoHighLevel session"""
    def wrapper(request, *args, **kwargs):
        # Check if user has a valid session
        user_data = request.session.get('ghl_user_data')
        if user_data:
            # User has valid session, add user data to request
            request.ghl_user = user_data
            return view_func(request, *args, **kwargs)
        else:
            # No session, redirect to user identification
            return redirect('ghl_integration:user_identification')
    return wrapper

def ghl_app_integration(request):
    """
    Main GoHighLevel app integration view
    Checks for existing session first, then shows appropriate content
    """
    # Check if user has existing session
    user_data = request.session.get('ghl_user_data')
    
    if user_data:
        # User has valid session, show authenticated content
        print(f"✅ User authenticated via session:")
        print(f"   User ID: {user_data['user_id']}")
        print(f"   Email: {user_data['user_email']}")
        print(f"   User Name: {user_data.get('user_name', 'N/A')}")
        print(f"   User Role: {user_data.get('user_role', 'N/A')}")
        print(f"   Company ID: {user_data['company_id']}")
        print(f"   Company Name: {user_data.get('company_name', 'N/A')}")
        print(f"   Location ID: {user_data['location_id']}")
        print(f"   Location Name: {user_data.get('location_name', 'N/A')}")
        print(f"   Session Version: {user_data.get('session_version', '1.0')}")
        print(f"   Detection Methods: {', '.join(user_data.get('detection_methods', []))}")
        
        # Display GHL context if available
        if 'ghl_context' in user_data:
            print(f"   GHL Context: {list(user_data['ghl_context'].keys())}")
        
        # Check if we have an integration for this location
        try:
            integration = GoHighLevelIntegration.objects.get(location_id=user_data['location_id'])
            print(f"   ✅ Found GoHighLevel integration: {integration.id}")
            
            # Check if WhatsApp access token exists for this location
            has_whatsapp_token = False
            try:
                whatsapp_token = WhatsAppAccessToken.objects.get(integration=integration)
                has_whatsapp_token = True
                print(f"   WhatsApp Token: ✅ Found")
            except WhatsAppAccessToken.DoesNotExist:
                print(f"   WhatsApp Token: ❌ Not configured")
                print(f"   This should show the connection form")
            
            print(f"   Final has_whatsapp_token value: {has_whatsapp_token}")
            
            # Render the authenticated template
            return render(request, 'ghl_integration/ghl_app_integration.html', {
                'is_authenticated': True,
                'user_data': user_data,
                'has_whatsapp_token': has_whatsapp_token,
                'session_created': user_data.get('session_created'),
                'last_activity': user_data.get('last_activity')
            })
            
        except GoHighLevelIntegration.DoesNotExist:
            print(f"   ❌ No GoHighLevel integration found for location: {user_data['location_id']}")
            # Still render the template but show no integration message
            return render(request, 'ghl_integration/ghl_app_integration.html', {
                'is_authenticated': True,
                'user_data': user_data,
                'has_whatsapp_token': False,
                'session_created': user_data.get('session_created'),
                'last_activity': user_data.get('last_activity')
            })
    
    else:
        # No session, show unauthenticated content
        print("ℹ️ No user session found, showing unauthenticated content")
        context = {
            'is_authenticated': False,
            'message': 'Please authenticate with GoHighLevel to continue'
        }
        return render(request, 'ghl_integration/ghl_app_integration.html', context)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def logout_user(request):
    """
    Handle user logout and clear session
    """
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    try:
        # Clear the GoHighLevel user session
        if 'ghl_user_data' in request.session:
            user_data = request.session['ghl_user_data']
            print(f"🚪 User logging out:")
            print(f"   User ID: {user_data.get('user_id')}")
            print(f"   Email: {user_data.get('user_email')}")
            print(f"   User Name: {user_data.get('user_name', 'N/A')}")
            print(f"   User Role: {user_data.get('user_role', 'N/A')}")
            print(f"   Company ID: {user_data.get('company_id')}")
            print(f"   Company Name: {user_data.get('company_name', 'N/A')}")
            print(f"   Location ID: {user_data.get('location_id')}")
            print(f"   Location Name: {user_data.get('location_name', 'N/A')}")
            print(f"   Session Version: {user_data.get('session_version', '1.0')}")
            print(f"   Detection Methods: {', '.join(user_data.get('detection_methods', []))}")
            
            # Display GHL context if available
            if 'ghl_context' in user_data:
                print(f"   GHL Context: {list(user_data['ghl_context'].keys())}")
            
            # Clear the session
            del request.session['ghl_user_data']
            request.session.flush()
            
            print("✅ Session cleared successfully")
            
        else:
            print("ℹ️ No user session found to clear")

        return JsonResponse({
            'success': True,
            'message': 'Logged out successfully'
        })

    except Exception as e:
        print(f"❌ Logout error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def check_session(request):
    """
    Check current session status
    """
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    try:
        # Check if user has existing session
        user_data = request.session.get('ghl_user_data')
        
        if user_data:
            print(f"✅ Session check - User authenticated:")
            print(f"   User ID: {user_data['user_id']}")
            print(f"   Email: {user_data['user_email']}")
            print(f"   User Name: {user_data.get('user_name', 'N/A')}")
            print(f"   User Role: {user_data.get('user_role', 'N/A')}")
            print(f"   Company ID: {user_data['company_id']}")
            print(f"   Company Name: {user_data.get('company_name', 'N/A')}")
            print(f"   Location ID: {user_data['location_id']}")
            print(f"   Location Name: {user_data.get('location_name', 'N/A')}")
            print(f"   Session created: {user_data.get('session_created')}")
            print(f"   Last activity: {user_data.get('last_activity')}")
            print(f"   Session version: {user_data.get('session_version', '1.0')}")
            print(f"   Detection methods: {', '.join(user_data.get('detection_methods', []))}")
            
            # Display GHL context if available
            if 'ghl_context' in user_data:
                print(f"   GHL Context available: {list(user_data['ghl_context'].keys())}")
            
            return JsonResponse({
                'success': True,
                'is_authenticated': True,
                'user_data': user_data,
                'session_id': request.session.session_key,
                'timestamp': timezone.now().isoformat()
            })
        else:
            print("ℹ️ Session check - No user session found")
            return JsonResponse({
                'success': True,
                'is_authenticated': False,
                'message': 'No active session found',
                'timestamp': timezone.now().isoformat()
            })

    except Exception as e:
        print(f"❌ Session check error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
