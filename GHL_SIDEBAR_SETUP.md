# 🚀 GoHighLevel Sidebar Integration Setup Guide

## Overview
This guide will help you set up your WhatReach app to appear **automatically in the GoHighLevel sidebar** after installation, just like other official GoHighLevel apps.

## 🎯 What We're Building
- **Automatic sidebar appearance** after app installation
- **Native GoHighLevel integration** using the app manifest system
- **Professional sidebar widget** with your app's branding
- **Seamless user experience** - no manual widget setup needed

## 📋 Prerequisites
- ✅ Django app running and accessible
- ✅ GoHighLevel OAuth integration working
- ✅ App manifest endpoint accessible
- ✅ Sidebar integration view working

## 🔧 Step 1: Verify Your App Manifest

### Test the Manifest Endpoint
```bash
# Start your server
python manage.py runserver

# Test the manifest
curl https://814e0c0adec4.ngrok-free.app/app/manifest.json
```

**Expected Response:**
```json
{
  "name": "WhatReach",
  "description": "GoHighLevel Integration App for Lead Management",
  "type": "private",
  "sidebar": {
    "enabled": true,
    "show_in_sidebar": true,
    "position": "left"
  }
  // ... more configuration
}
```

## 🚀 Step 2: Install Your App in GoHighLevel

### Method A: Direct Installation (Recommended)
1. **Go to your app's install URL:**
   ```
   https://814e0c0adec4.ngrok-free.app/app/install/
   ```

2. **Complete the OAuth flow**
3. **Wait for the webhook to complete installation**
4. **Check GoHighLevel sidebar** - your app should appear automatically!

### Method B: Manual App Addition
1. **Go to GoHighLevel → Settings → Apps**
2. **Look for "Custom Apps" or "Private Apps"**
3. **Click "Add App" or "Install App"**
4. **Enter your app's manifest URL:**
   ```
   https://814e0c0adec4.ngrok-free.app/app/manifest.json
   ```
5. **Complete the installation process**

## 🎨 Step 3: Verify Sidebar Integration

### What to Look For
After successful installation, you should see:

✅ **WhatReach icon** in the left sidebar
✅ **App name** displayed in sidebar
✅ **Clickable sidebar item** that opens your app
✅ **Proper positioning** (left side, top of sidebar)

### If the App Doesn't Appear
1. **Check GoHighLevel logs** for installation errors
2. **Verify manifest accessibility** (no CORS issues)
3. **Check app permissions** in GoHighLevel
4. **Ensure webhook completed** successfully

## 🔍 Step 4: Test Sidebar Functionality

### Test the Sidebar View
1. **Click on your app in the sidebar**
2. **Verify it opens properly**
3. **Check if location/user data loads**
4. **Test all sidebar buttons**

### Test URL:
```
https://814e0c0adec4.ngrok-free.app/app/sidebar/
```

## 🛠️ Step 5: Troubleshooting

### Common Issues & Solutions

#### Issue 1: App Not Appearing in Sidebar
**Symptoms:** App installed but no sidebar icon
**Solutions:**
- Check manifest.json accessibility
- Verify `sidebar.enabled: true`
- Check GoHighLevel app settings
- Ensure proper permissions

#### Issue 2: Sidebar Opens but No Content
**Symptoms:** Sidebar opens but shows blank/error
**Solutions:**
- Check sidebar view URL accessibility
- Verify X-Frame-Options headers
- Check browser console for errors
- Test sidebar view directly

#### Issue 3: Permission Denied
**Symptoms:** App shows but can't access features
**Solutions:**
- Check OAuth scopes in manifest
- Verify token permissions
- Check GoHighLevel app permissions
- Ensure proper user roles

## 📱 Step 6: Customize Sidebar Appearance

### Modify the Sidebar Template
Edit: `ghl_integration/templates/ghl_integration/sidebar.html`

### Customize Colors
Edit: `ghl_integration/static/ghl_integration/icon.svg`

### Adjust Layout
Edit: `ghl_integration/views.py` → `sidebar_integration` function

## 🎯 Step 7: Production Deployment

### Update Domain References
1. **Change ngrok URL to your production domain** in all URLs
2. **Update manifest.json** base_url
3. **Ensure HTTPS** (GoHighLevel requirement)
4. **Test all endpoints** on production domain

### Example Production URLs:
```bash
# Manifest
https://yourdomain.com/app/manifest.json

# Sidebar
https://yourdomain.com/app/sidebar/

# Install
https://yourdomain.com/app/install/

# Callback
https://yourdomain.com/app/callback/
```

## 🔒 Step 8: Security & Permissions

### Required GoHighLevel Permissions
```json
"permissions": [
  "contacts.readonly",
  "contacts.write", 
  "locations.readonly",
  "users.readonly",
  "app.install",
  "app.uninstall",
  "sidebar.access",
  "navigation.access"
]
```

### OAuth Scopes
```json
"scopes": [
  "contacts.readonly",
  "contacts.write",
  "locations.readonly", 
  "users.readonly",
  "sidebar.access",
  "navigation.access"
]
```

## 📊 Step 9: Monitoring & Analytics

### Check Integration Status
```bash
# View all integrations
https://814e0c0adec4.ngrok-free.app/app/list/

# Check specific integration
https://814e0c0adec4.ngrok-free.app/app/status/{integration_id}/

# Token health
https://814e0c0adec4.ngrok-free.app/app/token-health/
```

### Monitor Webhook Events
- Check webhook logs in Django admin
- Monitor GoHighLevel app events
- Track installation/uninstallation

## 🎉 Success Indicators

Your GoHighLevel sidebar integration is working when:

✅ **App appears automatically** in sidebar after installation
✅ **Sidebar icon is visible** and clickable
✅ **App opens properly** when sidebar item is clicked
✅ **All functionality works** within the sidebar
✅ **No manual widget setup** required
✅ **Professional appearance** matching GoHighLevel design

## 🆘 Getting Help

### If Still Not Working:
1. **Check Django logs** for errors
2. **Verify all URLs** are accessible
3. **Test manifest.json** endpoint
4. **Check GoHighLevel app settings**
5. **Verify OAuth flow** completed successfully
6. **Check webhook processing**

### Debug Commands:
```bash
# Test manifest
curl -v https://814e0c0adec4.ngrok-free.app/app/manifest.json

# Test sidebar
curl -v https://814e0c0adec4.ngrok-free.app/app/sidebar/

# Check Django logs
python manage.py runserver --verbosity=2
```

## 🚀 Next Steps

Once your sidebar integration is working:

1. **Customize the sidebar appearance**
2. **Add more sidebar features**
3. **Implement sidebar-specific functionality**
4. **Add analytics tracking**
5. **Optimize for mobile sidebar**

---

**Your WhatReach app should now appear automatically in the GoHighLevel sidebar after installation!** 🎉

If you're still having issues, the problem is likely in the GoHighLevel app configuration or permissions, not in your Django code.
