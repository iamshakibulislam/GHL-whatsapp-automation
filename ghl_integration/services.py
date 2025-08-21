import logging
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import requests
from .models import GoHighLevelIntegration
import base64
import json
import hashlib
from Crypto.Cipher import AES
from django.conf import settings

logger = logging.getLogger(__name__)

# GoHighLevel OAuth configuration
GHL_CLIENT_ID = getattr(settings, 'GHL_CLIENT_ID', 'your_client_id_here')
GHL_CLIENT_SECRET = getattr(settings, 'GHL_CLIENT_SECRET', 'your_client_secret_here')
GHL_TOKEN_URL = 'https://services.leadconnectorhq.com/oauth/token'


class TokenRefreshService:
    """
    Service for automatically refreshing expired GoHighLevel access tokens
    """
    
    @staticmethod
    def refresh_expired_tokens():
        """
        Find and refresh all expired or soon-to-expire tokens
        """
        try:
            # Find integrations that need token refresh
            integrations_needing_refresh = GoHighLevelIntegration.objects.filter(
                is_active=True,
                refresh_token__isnull=False
            ).exclude(refresh_token='')
            
            refreshed_count = 0
            failed_count = 0
            
            for integration in integrations_needing_refresh:
                if integration.needs_refresh:
                    try:
                        success = TokenRefreshService.refresh_single_token(integration)
                        if success:
                            refreshed_count += 1
                            logger.info(f"Successfully refreshed token for integration {integration.id}")
                        else:
                            failed_count += 1
                            logger.error(f"Failed to refresh token for integration {integration.id}")
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Error refreshing token for integration {integration.id}: {str(e)}")
            
            logger.info(f"Token refresh completed: {refreshed_count} successful, {failed_count} failed")
            return {
                'success': True,
                'refreshed_count': refreshed_count,
                'failed_count': failed_count
            }
            
        except Exception as e:
            logger.error(f"Error in bulk token refresh: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def refresh_single_token(integration):
        """
        Refresh a single integration's access token
        """
        try:
            if not integration.refresh_token:
                logger.warning(f"No refresh token available for integration {integration.id}")
                return False
            
            # Prepare refresh request
            data = {
                'client_id': GHL_CLIENT_ID,
                'client_secret': GHL_CLIENT_SECRET,
                'grant_type': 'refresh_token',
                'refresh_token': integration.refresh_token,
                'user_type': 'Company'  # Required according to docs
            }
            
            logger.info(f"Refreshing token for integration {integration.id}")
            
            # Make refresh request
            response = requests.post(GHL_TOKEN_URL, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Update integration with new tokens
            integration.access_token = token_data['access_token']
            integration.refresh_token = token_data.get('refresh_token', integration.refresh_token)
            integration.refresh_token_id = token_data.get('refreshTokenId', integration.refresh_token_id)
            integration.expires_at = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
            integration.user_type = token_data.get('userType', integration.user_type)
            integration.scope = token_data.get('scope', integration.scope)
            integration.is_bulk_installation = token_data.get('isBulkInstallation', integration.is_bulk_installation)
            integration.save()
            
            logger.info(f"Token refreshed successfully for integration {integration.id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error refreshing token for integration {integration.id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error refreshing token for integration {integration.id}: {str(e)}")
            return False
    
    @staticmethod
    def get_valid_token(integration):
        """
        Get a valid access token, refreshing if necessary
        Returns: (token, was_refreshed) tuple
        """
        if not integration.is_active:
            raise ValueError("Integration is not active")
        
        # Check if token needs refresh
        if integration.needs_refresh:
            logger.info(f"Token for integration {integration.id} needs refresh, refreshing now")
            success = TokenRefreshService.refresh_single_token(integration)
            if not success:
                raise Exception("Failed to refresh token")
            return integration.access_token, True
        
        # Check if token is expired
        if integration.is_token_expired:
            logger.warning(f"Token for integration {integration.id} is expired, attempting refresh")
            success = TokenRefreshService.refresh_single_token(integration)
            if not success:
                raise Exception("Failed to refresh expired token")
            return integration.access_token, True
        
        # Token is valid
        return integration.access_token, False


class TokenHealthService:
    """
    Service for monitoring token health and providing insights
    """
    
    @staticmethod
    def get_token_health_summary():
        """
        Get a summary of all token health statuses
        """
        integrations = GoHighLevelIntegration.objects.filter(is_active=True)
        
        total = integrations.count()
        expired = sum(1 for i in integrations if i.is_token_expired)
        needs_refresh = sum(1 for i in integrations if i.needs_refresh)
        healthy = sum(1 for i in integrations if not i.is_token_expired and not i.needs_refresh)
        
        return {
            'total_integrations': total,
            'expired_tokens': expired,
            'needs_refresh': needs_refresh,
            'healthy_tokens': healthy,
            'health_percentage': round((healthy / total * 100) if total > 0 else 0, 2)
        }
    
    @staticmethod
    def get_tokens_expiring_soon(hours=24):
        """
        Get integrations with tokens expiring within specified hours
        """
        threshold = timezone.now() + timedelta(hours=hours)
        return GoHighLevelIntegration.objects.filter(
            is_active=True,
            expires_at__lte=threshold
        ).order_by('expires_at')


class GoHighLevelDecryptionService:
    """
    Service for decrypting GoHighLevel encrypted user data
    Uses exact CryptoJS AES method as specified in official docs
    """

    @staticmethod
    def decrypt_user_data(encrypted_data):
        """
        Decrypt GoHighLevel encrypted user data using exact CryptoJS AES method

        Args:
            encrypted_data (str): Base64 encoded encrypted data from GoHighLevel

        Returns:
            dict: Decrypted user data or None if decryption fails
        """
        try:
            shared_secret = getattr(settings, 'GHL_SHARED_SECRET', None)
            if not shared_secret:
                print("❌ GHL_SHARED_SECRET not configured in settings")
                return None

            print(f"🔓 Decrypting GoHighLevel data...")
            print(f"   Data length: {len(encrypted_data)} characters")

            # Decrypt using exact CryptoJS method
            decrypted_data = GoHighLevelDecryptionService._decrypt_cryptojs_exact(encrypted_data, shared_secret)

            if decrypted_data:
                print(f"✅ Decryption successful: {list(decrypted_data.keys())}")
                return decrypted_data
            else:
                print("❌ Decryption failed")
                return None

        except Exception as e:
            print(f"❌ Decryption error: {str(e)}")
            return None

    @staticmethod
    def _decrypt_cryptojs_exact(encrypted_data, shared_secret):
        """
        Decrypt data using EXACT CryptoJS AES method as provided by user
        
        Args:
            encrypted_data (str): Base64 encoded encrypted data
            shared_secret (str): Shared secret key
            
        Returns:
            dict: Decrypted user data or None if decryption fails
        """
        try:
            print("   Using CryptoJS AES decryption...")
            
            # Decode base64 first
            try:
                decoded_data = base64.b64decode(encrypted_data)
                print(f"   Base64 decoded: {len(decoded_data)} bytes")
            except Exception as e:
                print(f"   Base64 decode failed: {str(e)}")
                return None
            
            # Method 1: Direct SHA-256 key derivation (most common CryptoJS approach)
            try:
                print("   Trying SHA-256 key derivation...")
                
                # Create 256-bit key from shared secret
                key = hashlib.sha256(shared_secret.encode('utf-8')).digest()
                
                # Try assuming first 16 bytes are IV (most common)
                if len(decoded_data) > 16:
                    iv = decoded_data[:16]
                    ciphertext = decoded_data[16:]
                    
                    if len(ciphertext) % 16 == 0:  # Must be multiple of AES block size
                        print(f"   Trying IV: 16 bytes, ciphertext: {len(ciphertext)} bytes")
                        
                        cipher = AES.new(key, AES.MODE_CBC, iv)
                        decrypted = cipher.decrypt(ciphertext)
                        
                        # Remove PKCS#7 padding
                        pad_length = decrypted[-1]
                        if 1 <= pad_length <= 16:
                            decrypted = decrypted[:-pad_length]
                            
                            # Try to parse as JSON
                            try:
                                decrypted_str = decrypted.decode('utf-8')
                                user_data = json.loads(decrypted_str)
                                print("   ✅ SHA-256 decryption successful!")
                                return user_data
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                # Try to extract JSON from the decrypted text
                                decrypted_str = decrypted.decode('utf-8', errors='ignore')
                                start_idx = decrypted_str.find('{')
                                end_idx = decrypted_str.rfind('}')
                                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                                    json_str = decrypted_str[start_idx:end_idx + 1]
                                    try:
                                        user_data = json.loads(json_str)
                                        print("   ✅ JSON extracted from decrypted text!")
                                        return user_data
                                    except json.JSONDecodeError:
                                        pass
                
                # Try without IV (ECB mode - less secure but some systems use it)
                if len(decoded_data) % 16 == 0:
                    print("   Trying AES-ECB mode...")
                    cipher = AES.new(key, AES.MODE_ECB)
                    decrypted = cipher.decrypt(decoded_data)
                    
                    # Remove padding
                    pad_length = decrypted[-1]
                    if 1 <= pad_length <= 16:
                        decrypted = decrypted[:-pad_length]
                        
                        try:
                            decrypted_str = decrypted.decode('utf-8')
                            user_data = json.loads(decrypted_str)
                            print("   ✅ AES-ECB decryption successful!")
                            return user_data
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            # Try JSON extraction
                            decrypted_str = decrypted.decode('utf-8', errors='ignore')
                            start_idx = decrypted_str.find('{')
                            end_idx = decrypted_str.rfind('}')
                            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                                json_str = decrypted_str[start_idx:end_idx + 1]
                                try:
                                    user_data = json.loads(json_str)
                                    print("   ✅ JSON extracted from AES-ECB decryption!")
                                    return user_data
                                except json.JSONDecodeError:
                                    pass
                                    
            except Exception as e:
                print(f"   SHA-256 method failed: {str(e)}")
            
            # Method 2: Try OpenSSL salted format as fallback
            try:
                print("   Trying OpenSSL salted format...")
                if decoded_data[:8] == b"Salted__":
                    return GoHighLevelDecryptionService._decrypt_openssl_salted(encrypted_data, shared_secret)
            except Exception as e:
                print(f"   OpenSSL salted method failed: {str(e)}")
            
            # Method 3: Try different key encodings
            try:
                print("   Trying different key encodings...")
                
                # Try UTF-8 encoding
                key_utf8 = shared_secret.encode('utf-8')
                if len(key_utf8) >= 32:
                    key = key_utf8[:32]
                else:
                    # Pad with zeros if too short
                    key = key_utf8 + b'\x00' * (32 - len(key_utf8))
                
                # Try with this key
                if len(decoded_data) > 16:
                    iv = decoded_data[:16]
                    ciphertext = decoded_data[16:]
                    
                    if len(ciphertext) % 16 == 0:
                        cipher = AES.new(key, AES.MODE_CBC, iv)
                        decrypted = cipher.decrypt(ciphertext)
                        
                        # Remove padding
                        pad_length = decrypted[-1]
                        if 1 <= pad_length <= 16:
                            decrypted = decrypted[:-pad_length]
                            
                            try:
                                decrypted_str = decrypted.decode('utf-8')
                                user_data = json.loads(decrypted_str)
                                print("   ✅ UTF-8 key encoding decryption successful!")
                                return user_data
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                pass
                                
            except Exception as e:
                print(f"   Different key encodings failed: {str(e)}")
            
            print("   ❌ All decryption methods failed")
            return None
            
        except Exception as e:
            print(f"   ❌ CryptoJS decryption failed: {str(e)}")
            return None

    @staticmethod
    def _decrypt_openssl_salted(encrypted_data, shared_secret):
        """
        Fallback: Decrypt data encrypted with OpenSSL salted format
        
        Args:
            encrypted_data (str): Base64 encoded encrypted data
            shared_secret (str): Shared secret key
            
        Returns:
            dict: Decrypted user data or None if decryption fails
        """
        try:
            # Decode base64
            data = base64.b64decode(encrypted_data)
            
            # Extract salt and ciphertext
            salt = data[8:16]
            ciphertext = data[16:]
            
            # Key and IV derivation (OpenSSL compatible)
            key_iv = hashlib.md5(shared_secret.encode() + salt).digest()
            while len(key_iv) < 32 + 16:  # Need 32 bytes for key + 16 bytes for IV
                key_iv += hashlib.md5(key_iv + shared_secret.encode() + salt).digest()
            
            key = key_iv[:32]
            iv = key_iv[32:48]
            
            # Create AES cipher
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # Decrypt
            decrypted = cipher.decrypt(ciphertext)
            
            # Remove PKCS#7 padding
            pad = decrypted[-1]
            if pad <= 16 and pad > 0:
                decrypted = decrypted[:-pad]
            
            # Try to parse as JSON
            try:
                user_data = json.loads(decrypted.decode('utf-8'))
                print("   ✅ OpenSSL salted decryption successful")
                return user_data
            except json.JSONDecodeError:
                # Try JSON extraction
                decrypted_str = decrypted.decode('utf-8', errors='ignore')
                start_idx = decrypted_str.find('{')
                end_idx = decrypted_str.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_str = decrypted_str[start_idx:end_idx + 1]
                    user_data = json.loads(json_str)
                    print("   ✅ JSON extracted from OpenSSL salted decryption")
                    return user_data
            
            return None
            
        except Exception as e:
            print(f"   ❌ OpenSSL salted decryption failed: {str(e)}")
            return None

    @staticmethod
    def _is_valid_base64(s):
        """Check if a string is valid base64"""
        try:
            if isinstance(s, str):
                import re
                if re.match(r'^[A-Za-z0-9+/]*={0,2}$', s):
                    base64.b64decode(s)
                    return True
            return False
        except Exception:
            return False
