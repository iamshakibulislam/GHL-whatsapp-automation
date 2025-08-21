# GoHighLevel Integration App - Setup Guide

## 🚀 Quick Start

This guide will help you set up and run the GoHighLevel integration app in minutes.

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure GoHighLevel OAuth

1. **Get GoHighLevel App Credentials**
   - Go to [GoHighLevel Developer Portal](https://developer.gohighlevel.com/)
   - Create a new app
   - Set redirect URI to: `http://localhost:8000/app/callback/`
   - Copy your Client ID and Client Secret

2. **Update Settings**
   - Edit `whatreach/settings.py`
   - Replace placeholder values:
   ```python
   GHL_CLIENT_ID = 'your_actual_client_id'
   GHL_CLIENT_SECRET = 'your_actual_client_secret'
   GHL_REDIRECT_URI = 'http://localhost:8000/app/callback/'
   ```

### 3. Run Database Migrations

```bash
python manage.py migrate
```

### 4. Create Admin User (Optional)

```bash
python manage.py createsuperuser
```

### 5. Start the Server

```bash
python manage.py runserver
```

### 6. Test the Integration

1. **Visit Installation URL**: `http://localhost:8000/app/install/`
2. **Check Admin Panel**: `http://localhost:8000/admin/`
3. **Run Demo Script**: `python demo.py`

## 🔗 Available URLs

| URL | Purpose | Method |
|-----|---------|--------|
| `/app/install/` | Start OAuth installation | GET |
| `/app/callback/` | Handle OAuth callback | GET |
| `/app/refresh/{id}/` | Refresh access token | POST |
| `/app/status/{id}/` | Get integration status | GET |
| `/app/list/` | List all integrations | GET |
| `/app/webhook/` | Handle webhook events | POST |

## 📊 Database Models

### GoHighLevelIntegration
- Stores app installation data
- Manages OAuth tokens
- Tracks company and user information

### GoHighLevelWebhook
- Stores webhook events
- Links to integrations
- Tracks processing status

## 🛠️ Admin Features

- **Integration Management**: View, edit, and manage all integrations
- **Token Monitoring**: Track token expiration and refresh needs
- **Webhook Handling**: Process and manage webhook events
- **Bulk Actions**: Refresh tokens, deactivate integrations

## 🔐 Security Features

- CSRF protection on all endpoints
- Secure token storage
- UUID-based primary keys
- Automatic token refresh
- Webhook validation

## 🧪 Testing

Run the test suite:

```bash
python manage.py test ghl_integration
```

## 📝 Demo Script

Run the interactive demo:

```bash
python demo.py
```

This will:
- Create sample integrations
- Demonstrate token management
- Show webhook handling
- Provide database query examples

## 🌐 Production Deployment

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

## 🐛 Troubleshooting

### Common Issues

1. **OAuth Error**
   - Check client ID, secret, and redirect URI
   - Ensure redirect URI matches exactly

2. **Token Expired**
   - Tokens automatically refresh
   - Check if refresh token is available

3. **Webhook Failures**
   - Verify webhook endpoint is accessible
   - Check webhook URL in GoHighLevel

4. **Database Errors**
   - Run migrations: `python manage.py migrate`
   - Check database connection

### Debug Mode
Enable debug mode in development:
```python
DEBUG = True
```

## 📚 API Documentation

### OAuth Flow
1. User visits `/app/install/`
2. Redirected to GoHighLevel for authorization and location selection
3. GoHighLevel redirects back with `code` parameter (locationId may be included or determined later)
4. App exchanges code for access token, handling location selection as needed
5. Token, user info, and location details stored in database

### Token Management
- Access tokens expire (typically 1 hour)
- Refresh tokens used to get new access tokens
- Automatic refresh when tokens near expiration

### Webhook Processing
- Webhooks received at `/app/webhook/`
- Events stored and processed
- Integration status updated based on events

## 🎯 Next Steps

1. **Customize Scopes**: Modify OAuth scopes in `views.py`
2. **Add Business Logic**: Implement your app's core functionality
3. **Enhance Webhooks**: Add more webhook event handlers
4. **API Integration**: Use stored tokens to call GoHighLevel APIs
5. **User Interface**: Build custom UI for integration management

## 📞 Support

For issues and questions:
1. Check the logs for error details
2. Verify GoHighLevel app configuration
3. Ensure all dependencies are installed
4. Check database migrations
5. Review the test suite for examples

## 📄 License

This project is licensed under the MIT License.
