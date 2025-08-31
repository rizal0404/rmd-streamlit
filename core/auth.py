"""
Authentication module for Raw Mix Design Optimizer
Supports both Clerk integration and local authentication
"""

import streamlit as st
import requests
import jwt
import bcrypt
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWKClient


class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    pass


class ClerkAuth:
    """Clerk authentication integration"""
    
    def __init__(self, publishable_key: str, jwks_url: str = None, issuer: str = None):
        self.publishable_key = publishable_key
        self.jwks_url = jwks_url or f"https://{publishable_key.split('_')[2]}.clerk.accounts.dev/.well-known/jwks.json"
        self.issuer = issuer or f"https://{publishable_key.split('_')[2]}.clerk.accounts.dev"
        self.jwks_client = PyJWKClient(self.jwks_url) if jwks_url else None
        
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify Clerk JWT token using JWKS"""
        try:
            # Get the signing key from JWKS
            if self.jwks_client:
                signing_key = self.jwks_client.get_signing_key_from_jwt(token)
                key = signing_key.key
            else:
                # Fallback: For development, you might need to handle this differently
                raise AuthenticationError("JWKS client not configured")
            
            # Verify the token
            decoded = jwt.decode(
                token, 
                key, 
                algorithms=["RS256"],
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True
                }
            )
            
            return decoded
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"Token verification failed: {str(e)}")
    
    def get_user_from_token(self, token: str) -> Dict[str, Any]:
        """Extract user information from verified Clerk token"""
        try:
            payload = self.verify_token(token)
            
            # Extract user information from Clerk token payload
            user_info = {
                'id': payload.get('sub'),
                'email': payload.get('email'),
                'username': payload.get('email', '').split('@')[0],  # Use email prefix as username
                'full_name': f"{payload.get('given_name', '')} {payload.get('family_name', '')}".strip(),
                'first_name': payload.get('given_name', ''),
                'last_name': payload.get('family_name', ''),
                'email_verified': payload.get('email_verified', False),
                'auth_method': 'clerk',
                'clerk_user_id': payload.get('sub'),
                'last_login': datetime.now().isoformat()
            }
            
            # Clean up empty full_name
            if not user_info['full_name']:
                user_info['full_name'] = user_info['username']
                
            return user_info
            
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Failed to extract user info: {str(e)}")


class LocalAuth:
    """Local authentication for fallback"""
    
    def __init__(self, users_file: str = "data/users.json"):
        self.users_file = users_file
        self._ensure_users_file()
    
    def _ensure_users_file(self):
        """Ensure users file exists"""
        if not os.path.exists(self.users_file):
            os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
            default_users = {}
            with open(self.users_file, 'w') as f:
                json.dump(default_users, f)
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_user(self, username: str, email: str, password: str, full_name: str = "") -> bool:
        """Create a new user"""
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
            
            if username in users or any(u.get('email') == email for u in users.values()):
                return False  # User already exists
            
            users[username] = {
                "email": email,
                "password_hash": self.hash_password(password),
                "full_name": full_name,
                "created_at": datetime.now().isoformat(),
                "last_login": None
            }
            
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
            
            return True
        except Exception:
            return False
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user with username/password"""
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
            
            if username not in users:
                raise AuthenticationError("Invalid username or password")
            
            user = users[username]
            if not self.verify_password(password, user['password_hash']):
                raise AuthenticationError("Invalid username or password")
            
            # Update last login
            user['last_login'] = datetime.now().isoformat()
            users[username] = user
            
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
            
            # Return user info (without password hash)
            user_info = user.copy()
            del user_info['password_hash']
            user_info['username'] = username
            return user_info
            
        except FileNotFoundError:
            raise AuthenticationError("Authentication system not initialized")
        except json.JSONDecodeError:
            raise AuthenticationError("Authentication data corrupted")


class AuthManager:
    """Main authentication manager"""
    
    def __init__(self):
        self.clerk_auth = None
        self.local_auth = LocalAuth()
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Initialize Clerk if credentials are available
        clerk_publishable = os.getenv('CLERK_PUBLISHABLE_KEY')
        clerk_jwks_url = os.getenv('CLERK_JWKS_URL')
        clerk_issuer = os.getenv('CLERK_JWT_ISSUER')
        
        if clerk_publishable:
            try:
                self.clerk_auth = ClerkAuth(clerk_publishable, clerk_jwks_url, clerk_issuer)
            except Exception as e:
                print(f"Warning: Failed to initialize Clerk auth: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return 'authenticated' in st.session_state and st.session_state.authenticated
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current authenticated user"""
        if self.is_authenticated():
            return st.session_state.get('user_info')
        return None
    
    def login_with_clerk(self, token: str) -> Dict[str, Any]:
        """Login using Clerk token"""
        if not self.clerk_auth:
            raise AuthenticationError("Clerk authentication not configured")
        
        user_info = self.clerk_auth.get_user_from_token(token)
        self._set_session_user(user_info, 'clerk')
        return user_info
    
    def login_local(self, username: str, password: str) -> Dict[str, Any]:
        """Login using local authentication"""
        user_info = self.local_auth.authenticate_user(username, password)
        self._set_session_user(user_info, 'local')
        return user_info
    
    def register_local(self, username: str, email: str, password: str, full_name: str = "") -> bool:
        """Register new local user"""
        return self.local_auth.create_user(username, email, password, full_name)
    
    def logout(self):
        """Logout current user"""
        # Clear authentication state
        if 'authenticated' in st.session_state:
            del st.session_state.authenticated
        if 'user_info' in st.session_state:
            del st.session_state.user_info
        if 'auth_method' in st.session_state:
            del st.session_state.auth_method
        
        # Clear other session data that should not persist
        keys_to_clear = ['current_project_id', 'project_name']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def _set_session_user(self, user_info: Dict[str, Any], auth_method: str):
        """Set user session"""
        st.session_state.authenticated = True
        st.session_state.user_info = user_info
        st.session_state.auth_method = auth_method
    
    def require_auth(self):
        """Decorator/function to require authentication"""
        if not self.is_authenticated():
            st.error("Please log in to access this application.")
            st.stop()


def get_auth_config() -> Dict[str, Any]:
    """Get authentication configuration"""
    return {
        'clerk_enabled': os.getenv('CLERK_PUBLISHABLE_KEY') is not None,
        'local_auth_enabled': True,  # Always available as fallback
        'require_email_verification': os.getenv('REQUIRE_EMAIL_VERIFICATION', 'false').lower() == 'true',
        'session_timeout_hours': int(os.getenv('SESSION_TIMEOUT_HOURS', '24')),
        'max_login_attempts': int(os.getenv('MAX_LOGIN_ATTEMPTS', '5')),
    }


# Global auth manager instance
auth_manager = AuthManager()