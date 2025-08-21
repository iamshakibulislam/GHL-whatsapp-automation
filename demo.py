#!/usr/bin/env python
"""
Demo script for GoHighLevel Integration App
"""

print("🚀 WhatReach - GoHighLevel Integration Demo")
print("=" * 50)

# App URLs
base_url = "https://814e0c0adec4.ngrok-free.app"
app_urls = {
    "Install App": f"{base_url}/app/install/",
    "App Landing": f"{base_url}/app/",
    "App Manifest": f"{base_url}/app/manifest.json",
    "Sidebar Integration": f"{base_url}/app/sidebar/",
    "Sidebar Widget": f"{base_url}/app/sidebar-widget/",
    "List Integrations": f"{base_url}/app/list/",
    "Token Health": f"{base_url}/app/token-health/",
    "Test Connectivity": f"{base_url}/app/test-connectivity/",
}

print("\n📱 Available App Endpoints:")
for name, url in app_urls.items():
    print(f"  {name}: {url}")

print("\n🔧 Testing Commands:")
print(f"  # Test manifest")
print(f"  curl {base_url}/app/manifest.json")
print(f"  ")
print(f"  # Test sidebar")
print(f"  curl {base_url}/app/sidebar/")
print(f"  ")
print(f"  # Test connectivity")
print(f"  curl {base_url}/app/test-connectivity/")

print("\n🎯 Next Steps:")
print("  1. Start your Django server: python manage.py runserver")
print("  2. Test the manifest endpoint")
print("  3. Install the app in GoHighLevel")
print("  4. Check if it appears in the sidebar automatically!")

print("\n💡 Note: Make sure your ngrok tunnel is running and accessible!")
