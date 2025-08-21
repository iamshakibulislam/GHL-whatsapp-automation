# Linux Cron Setup Guide for GoHighLevel Token Refresh

This guide shows you how to set up automatic token refresh using `django-crontab` on Linux systems.

## 🚀 **Prerequisites**

- Linux server with Python and Django installed
- `django-crontab` package installed
- GoHighLevel integration app running

## 📦 **Installation**

1. **Install django-crontab:**
   ```bash
   pip install django-crontab
   ```

2. **Add to Django settings:**
   ```python
   INSTALLED_APPS = [
       # ... other apps
       'django_crontab',
       'ghl_integration',
   ]
   
   # Cron configuration
   CRONJOBS = [
       # Refresh tokens every hour
       ('0 * * * *', 'ghl_integration.cron.refresh_expired_tokens'),
       
       # Daily health check at 2 AM
       ('0 2 * * *', 'ghl_integration.cron.daily_token_health_check'),
       
       # Weekly bulk refresh on Sundays at 3 AM
       ('0 3 * * 0', 'ghl_integration.cron.weekly_bulk_refresh'),
   ]
   
   CRONTAB_LOCK_JOBS = True
   CRONTAB_COMMAND_PREFIX = 'DJANGO_SETTINGS_MODULE=yourproject.settings'
   CRONTAB_PYTHON_EXECUTABLE = 'python'
   ```

## ⚙️ **Setup Commands**

### **1. Add cron jobs to system crontab:**
   ```bash
   python manage.py crontab add
   ```

### **2. View current cron jobs:**
   ```bash
   python manage.py crontab show
   ```

### **3. Remove cron jobs:**
   ```bash
   python manage.py crontab remove
   ```

### **4. Show system crontab:**
   ```bash
   crontab -l
   ```

## 🕐 **Cron Schedule**

| Job | Schedule | Description |
|-----|----------|-------------|
| **Hourly Token Refresh** | `0 * * * *` | Refreshes expired tokens every hour |
| **Daily Health Check** | `0 2 * * *` | Comprehensive token health analysis at 2 AM |
| **Weekly Bulk Refresh** | `0 3 * * 0` | Bulk refresh all tokens on Sundays at 3 AM |

## 🔍 **Manual Testing**

Test the cron functions manually:

```bash
# Test hourly refresh
python manage.py shell
>>> from ghl_integration.cron import refresh_expired_tokens
>>> result = refresh_expired_tokens()
>>> print(result)

# Test daily health check
>>> from ghl_integration.cron import daily_token_health_check
>>> health = daily_token_health_check()
>>> print(health)

# Test weekly bulk refresh
>>> from ghl_integration.cron import weekly_bulk_refresh
>>> result = weekly_bulk_refresh()
>>> print(result)
```

## 📊 **Monitoring**

### **Check cron job status:**
```bash
# View cron logs
tail -f /var/log/cron

# Check Django logs
tail -f /path/to/your/django/logs

# View system crontab
crontab -l
```

### **Verify cron jobs are running:**
```bash
# Check if cron service is running
sudo systemctl status cron

# Restart cron service if needed
sudo systemctl restart cron
```

## 🚨 **Troubleshooting**

### **Common Issues:**

1. **Cron jobs not running:**
   - Check if cron service is running: `sudo systemctl status cron`
   - Verify crontab entries: `crontab -l`
   - Check Django settings path in `CRONTAB_COMMAND_PREFIX`

2. **Permission errors:**
   - Ensure Django app has proper permissions
   - Check file paths in cron commands

3. **Environment issues:**
   - Verify `DJANGO_SETTINGS_MODULE` is correct
   - Check Python path in `CRONTAB_PYTHON_EXECUTABLE`

### **Debug Commands:**
```bash
# Test cron syntax
python manage.py crontab show

# Check Django settings
python manage.py check

# Test individual functions
python manage.py shell -c "from ghl_integration.cron import refresh_expired_tokens; print(refresh_expired_tokens())"
```

## 🔧 **Advanced Configuration**

### **Custom Cron Schedules:**

```python
CRONJOBS = [
    # Every 30 minutes during business hours (9 AM - 6 PM, Mon-Fri)
    ('0,30 9-18 * * 1-5', 'ghl_integration.cron.refresh_expired_tokens'),
    
    # Twice daily (6 AM and 6 PM)
    ('0 6,18 * * *', 'ghl_integration.cron.refresh_expired_tokens'),
    
    # Every 15 minutes during peak hours
    ('*/15 8-20 * * *', 'ghl_integration.cron.refresh_expired_tokens'),
]
```

### **Environment Variables:**
```python
CRONTAB_COMMAND_PREFIX = 'DJANGO_SETTINGS_MODULE=yourproject.settings DJANGO_ENV=production'
```

## 📈 **Performance Tips**

1. **Use lock files** to prevent multiple instances
2. **Monitor memory usage** during bulk operations
3. **Set appropriate timeouts** for token refresh operations
4. **Log rotation** for cron job logs

## 🎯 **Production Checklist**

- [ ] Cron service is running
- [ ] Django app is accessible
- [ ] Database connections are stable
- [ ] Logging is configured
- [ ] Error notifications are set up
- [ ] Backup procedures are in place

## 📞 **Support**

If you encounter issues:

1. Check Django logs for errors
2. Verify cron service status
3. Test functions manually
4. Review system crontab entries
5. Check file permissions and paths

---

**Note:** This setup is designed for Linux systems. For Windows, use Windows Task Scheduler instead.
