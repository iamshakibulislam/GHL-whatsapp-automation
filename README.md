# WhatReach - GoHighLevel Integration App

A Django-based GoHighLevel app that handles OAuth authentication and stores access tokens when users install the app.

## Features

- **OAuth Integration**: Complete OAuth 2.0 flow for GoHighLevel app installation
- **Token Management**: Secure storage and automatic refresh of access tokens
- **Webhook Support**: Handle webhook events from GoHighLevel
- **Admin Interface**: Comprehensive admin panel for managing integrations
- **API Endpoints**: RESTful API for integration management

## Installation

### Prerequisites

- Python 3.8+
- Django 5.2+
- GoHighLevel Developer Account

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd whatreach
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure GoHighLevel OAuth**
   
   Update `whatreach/settings.py` with your GoHighLevel app credentials:
   ```python
   GHL_CLIENT_ID = 'your_actual_client_id'
   GHL_CLIENT_SECRET = 'your_actual_client_secret'
   GHL_REDIRECT_URI = 'https://yourdomain.com/ghl/callback/'
   ```

4. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## GoHighLevel App Configuration

### 1. Create GoHighLevel App

1. Go to [GoHighLevel Developer Portal](https://developer.gohighlevel.com/)
2. Create a new app
3. Set the redirect URI to: `https://yourdomain.com/app/callback/`
4. Note down your Client ID and Client Secret

### 2. API Endpoints Used

The app connects to these GoHighLevel services:
- **OAuth Authorization**: `https://marketplace.gohighlevel.com/oauth/chooselocation`
- **Token Exchange**: `https://services.leadconnectorhq.com/oauth/token`
- **API Access**: `https://rest.gohighlevel.com/v1/`

### 2. App Installation Flow

1. **Installation URL**: `https://yourdomain.com/app/install/`
2. **OAuth Flow**: Users are redirected to GoHighLevel for authorization and location selection
3. **Callback**: GoHighLevel redirects back with `code` parameter (locationId may be included or determined later)
4. **Token Exchange**: App exchanges code for access token, handling location selection as needed
5. **Storage**: Access token, user info, and location details are stored in database

## API Endpoints

### OAuth Flow
- `GET /ghl/install/` - Start OAuth installation process
- `GET /ghl/callback/` - Handle OAuth callback

### Token Management

#### **Automatic Token Refresh System** 🚀

Our GoHighLevel app includes a **comprehensive automatic token refresh system** that ensures your app never stops working due to expired tokens!

#### **How It Works:**

1. **Smart Detection**: 
   - Monitors token expiration (24 hours)
   - Detects when tokens need refresh (within 1 hour of expiration)
   - Automatically refreshes before API calls

2. **Multiple Refresh Methods**:
   - **Middleware**: Automatically refreshes tokens before API requests
   - **Management Command**: Scheduled bulk refresh for all integrations
   - **Manual API**: Trigger refresh via REST endpoints
   - **Admin Actions**: Bulk refresh from Django admin

3. **Token Health Monitoring**:
   - Real-time token health dashboard
   - Percentage of healthy tokens
   - Expired token alerts
   - Integration status overview

#### **API Endpoints:**

- `POST /app/refresh/{integration_id}/` - Refresh access token
- `GET /app/status/{integration_id}/` - Get integration status
- `GET /app/token-health/` - Get overall token health summary
- `POST /app/bulk-refresh/` - Manually trigger bulk token refresh
- `GET /app/get-token/{integration_id}/` - Get valid token (refreshes if needed)

#### **Management Commands:**

```bash
# Check token health (dry run)
python manage.py refresh_ghl_tokens --dry-run

# Refresh all expired tokens
python manage.py refresh_ghl_tokens

# Force refresh all tokens
python manage.py refresh_ghl_tokens --force
```

#### **Automatic Cron Jobs (Linux):**

```bash
# Add cron jobs to system crontab
python manage.py crontab add

# View current cron jobs
python manage.py crontab show

# Remove cron jobs
python manage.py crontab remove
```

**Cron Schedule:**
- **Hourly**: Token refresh every hour
- **Daily**: Health check at 2 AM
- **Weekly**: Bulk refresh on Sundays at 3 AM

### Integration Management
- `GET /ghl/list/` - List all integrations
- `POST /ghl/webhook/` - Handle webhook events

## Models

### GoHighLevelIntegration
Stores app installation data and OAuth tokens:
- Location information (ID, name, company details)
- User information (ID, email)
- OAuth tokens (access, refresh, expiration)
- Installation metadata

### GoHighLevelWebhook
Stores webhook events from GoHighLevel:
- Event type and data
- Associated integration
- Processing status

## Admin Interface

Access the admin panel at `/admin/` to:
- View and manage all integrations
- Monitor token status and expiration
- Handle webhook events
- **Bulk token refresh** - Refresh multiple tokens at once
- **Token health dashboard** - Overview of all integration statuses
- **Complete token data** - View all stored token information
- Deactivate integrations
- **Token metadata** - User type, scope, bulk installation status

## Webhook Events

The app handles these webhook events:
- `app.installed` - App installation
- `app.uninstalled` - App uninstallation
- Custom events based on your app's needs

## Security Features

- CSRF protection on all endpoints
- Secure token storage
- UUID-based primary keys
- Automatic token refresh
- Webhook validation

## Production Deployment

### Environment Variables
```bash
export GHL_CLIENT_ID='your_client_id'
export GHL_CLIENT_SECRET='your_client_secret'
export GHL_REDIRECT_URI='https://yourdomain.com/app/callback/'
export DJANGO_SECRET_KEY='your_secret_key'
export DJANGO_DEBUG='False'
```

### HTTPS Required
- GoHighLevel requires HTTPS for production
- Update `GHL_REDIRECT_URI` to use HTTPS
- Configure SSL certificates

### Database
- Use PostgreSQL or MySQL for production
- Update `DATABASES` setting in `settings.py`

## Development

### Running Tests
```bash
python manage.py test ghl_integration
```

### Code Style
- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to functions and classes

## Troubleshooting

### Common Issues

1. **OAuth Error**: Check client ID, secret, and redirect URI
2. **Token Expired**: Tokens automatically refresh, check refresh token
3. **Webhook Failures**: Verify webhook endpoint is accessible
4. **Database Errors**: Run migrations and check database connection
5. **OAuth 400 Bad Request**: 
   - Ensure GoHighLevel app is configured with correct redirect URI
   - Verify that `locationId` is being sent in OAuth callback
   - Check OAuth scopes and permissions
6. **Connectivity Issues**: 
   - Use the `/app/test-connectivity/` endpoint for debugging
   - Check firewall and network settings
   - Verify GoHighLevel service status

### Debug Mode
Enable debug mode in development to see detailed error messages:
```python
DEBUG = True
```

## Support

For issues and questions:
1. Check the logs for error details
2. Verify GoHighLevel app configuration
3. Ensure all dependencies are installed
4. Check database migrations

## License

This project is licensed under the MIT License.
