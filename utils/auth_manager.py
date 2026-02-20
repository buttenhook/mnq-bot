#!/usr/bin/env python3
"""
Tradovate Authentication Manager
Handles: token acquisition, renewal, session management
"""

import os
import time
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class TradovateAuth:
    """
    Manages Tradovate API authentication.
    
    Key Rules:
    - Tokens expire in 90 minutes (renew at 75)
    - Max 2 concurrent sessions
    - Use Bearer token for all requests
    - Separate mdAccessToken for WebSocket
    """
    
    def __init__(self):
        self._load_credentials()
        self.access_token: Optional[str] = None
        self.md_access_token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.account_id: Optional[int] = None
        self.token_created: Optional[datetime] = None
        self.renew_threshold = timedelta(minutes=75)
        self.base_url = self._get_base_url()
        
    def _load_credentials(self):
        """Load from environment"""
        self.username = os.getenv("TRADOVATE_USERNAME")
        self.password = os.getenv("TRADOVATE_PASSWORD")
        self.api_secret = os.getenv("TRADOVATE_API_SECRET")
        self.account_id_from_env = os.getenv("TRADOVATE_ACCOUNT_ID")
        
        if not all([self.username, self.password, self.api_secret]):
            raise ValueError("Set TRADOVATE_USERNAME, PASSWORD, and API_SECRET")
    
    def _get_base_url(self) -> str:
        """Get base URL based on mode"""
        mode = os.getenv("TRADOVATE_MODE", "demo")
        return f"https://{mode}.tradovateapi.com/v1"
    
    @property
    def ws_url(self) -> str:
        """
        Get WebSocket URL for market data.
        
        Per official docs:
        - Demo: Same md.tradovateapi.com with demo credentials
        - Both use wss://, auth token separates demo/live
        """
        return "wss://md.tradovateapi.com/v1/websocket"
    
    async def authenticate(self) -> bool:
        """
        Get access token from Tradovate.
        
        POST /auth/accessTokenRequest
        """
        url = f"{self.base_url}/auth/accessTokenRequest"
        
        payload = {
            "name": self.username,
            "password": self.password,
            "appId": "WolfBot",
            "appVersion": "1.0",
            "cid": 0,
            "sec": self.api_secret
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        print(f"Auth failed: {resp.status}")
                        return False
                    
                    data = await resp.json()
                    
                    self.access_token = data.get("accessToken")
                    self.md_access_token = data.get("mdAccessToken")
                    self.user_id = data.get("userId")
                    self.account_id = data.get("accountId") or self.account_id_from_env
                    self.token_created = datetime.now()
                    
                    print(f"✅ Authenticated. User: {self.user_id}, Account: {self.account_id}")
                    return True
                    
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    async def renew_token(self) -> bool:
        """
        Renew access token before expiry.
        
        Call at 75 minutes, token expires at 90.
        POST /auth/renewAccessToken
        """
        if not self.access_token:
            return await self.authenticate()
        
        url = f"{self.base_url}/auth/renewAccessToken"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.access_token = data.get("accessToken")
                        self.token_created = datetime.now()
                        print("✅ Token renewed")
                        return True
                    else:
                        print(f"Renewal failed: {resp.status}")
                        return await self.authenticate()
        except Exception as e:
            print(f"Renewal error: {e}")
            return await self.authenticate()
    
    async def auto_renew(self):
        """Background task: auto-renew token before expiry"""
        while True:
            await asyncio.sleep(60)  # Check every minute
            
            if not self.token_created:
                continue
            
            elapsed = datetime.now() - self.token_created
            if elapsed >= self.renew_threshold:
                print("Renewing token (75min reached)...")
                await self.renew_token()
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers for authenticated requests"""
        if not self.access_token:
            raise RuntimeError("Not authenticated")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def is_authenticated(self) -> bool:
        """Check if we have active token"""
        return self.access_token is not None


# Test
def test_auth():
    import asyncio
    
    async def run():
        auth = TradovateAuth()
        success = await auth.authenticate()
        print(f"Auth success: {success}")
        print(f"Token: {auth.access_token[:20]}...")
    
    asyncio.run(run())


if __name__ == "__main__":
    test_auth()
