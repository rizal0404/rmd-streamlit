"""
Test script to verify Clerk authentication configuration
"""

import sys
import os
from pathlib import Path

# Add the project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from core.auth import auth_manager, get_auth_config

def test_clerk_config():
    """Test Clerk configuration"""
    print("🔧 Testing Clerk Authentication Configuration...")
    
    # Load environment variables
    load_dotenv()
    
    # Check environment variables
    clerk_publishable = os.getenv('CLERK_PUBLISHABLE_KEY')
    clerk_jwks_url = os.getenv('CLERK_JWKS_URL')
    clerk_issuer = os.getenv('CLERK_JWT_ISSUER')
    
    print(f"📋 Environment Variables:")
    print(f"   CLERK_PUBLISHABLE_KEY: {'✅ Set' if clerk_publishable else '❌ Not set'}")
    print(f"   CLERK_JWKS_URL: {'✅ Set' if clerk_jwks_url else '❌ Not set'}")
    print(f"   CLERK_JWT_ISSUER: {'✅ Set' if clerk_issuer else '❌ Not set'}")
    
    # Check auth configuration
    auth_config = get_auth_config()
    print(f"\n🔐 Authentication Configuration:")
    print(f"   Clerk Enabled: {'✅ Yes' if auth_config['clerk_enabled'] else '❌ No'}")
    print(f"   Local Auth Enabled: {'✅ Yes' if auth_config['local_auth_enabled'] else '❌ No'}")
    
    # Check auth manager
    print(f"\n🏗️ Auth Manager:")
    print(f"   Clerk Auth Instance: {'✅ Created' if auth_manager.clerk_auth else '❌ Not created'}")
    print(f"   Local Auth Instance: {'✅ Created' if auth_manager.local_auth else '❌ Not created'}")
    
    if auth_manager.clerk_auth:
        print(f"   Clerk JWKS URL: {auth_manager.clerk_auth.jwks_url}")
        print(f"   Clerk Issuer: {auth_manager.clerk_auth.issuer}")
    
    print(f"\n🎉 Configuration Status: {'✅ Ready for Clerk Authentication' if auth_config['clerk_enabled'] else '⚠️ Using Local Auth Only'}")

if __name__ == "__main__":
    test_clerk_config()