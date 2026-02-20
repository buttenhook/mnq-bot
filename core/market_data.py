#!/usr/bin/env python3
"""
Tradovate WebSocket Market Data Client
Handles: real-time quotes, DOM, position updates
"""

import json
import asyncio
import websockets
from typing import Callable, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Quote:
    symbol: str
    bid: float
    ask: float
    last: float
    bid_size: int
    ask_size: int
    volume: int
    timestamp: datetime


@dataclass  
class Position:
    symbol: str
    qty: int
    avg_entry: float
    unrealized_pnl: float
    timestamp: datetime


class MarketDataClient:
    """
    WebSocket client for real-time market data.
    
    WSS URLs (Official):
    - wss://md.tradovateapi.com/v1/websocket (both demo/live, auth token handles separation)
    
    Subscriptions:
    - md/subscribeQuote: Real-time quotes
    - md/subscribeDOM: Order book
    - user/syncRequest: Position updates
    """
    
    def __init__(self, auth_manager):
        self.auth = auth_manager
        self.ws = None
        self.connected = False
        
        # Handlers
        self.quote_handlers: list[Callable] = []
        self.position_handlers: list[Callable] = []
        
        # State
        self.quotes: Dict[str, Quote] = {}
        self.positions: Dict[str, Position] = {}
        
        # Subscription IDs
        self.subscriptions: Dict[str, int] = {}
        
    async def connect(self) -> bool:
        """Connect to WebSocket with auth"""
        if not self.auth.md_access_token:
            print("No MD access token. Authenticate first.")
            return False
        
        try:
            self.ws = await websockets.connect(self.auth.ws_url)
            
            # Authenticate WS
            auth_msg = {
                "token": self.auth.md_access_token
            }
            await self.ws.send(json.dumps(auth_msg))
            
            response = await self.ws.recv()
            print(f"WS Connected: {response}")
            
            self.connected = True
            
            # Start listener
            asyncio.create_task(self._listener())
            
            return True
            
        except Exception as e:
            print(f"WS connect error: {e}")
            return False
    
    async def subscribe_quote(self, symbol: str):
        """
        Subscribe to real-time quotes for symbol.
        
        MNQ symbols: MNQH6 (March), MNQM6 (June), etc.
        """
        if not self.ws:
            print("Not connected")
            return
        
        msg = {
            "url": "md/subscribeQuote",
            "body": {
                "symbol": symbol
            }
        }
        
        await self.ws.send(json.dumps(msg))
        print(f"Subscribed to quotes: {symbol}")
    
    async def subscribe_position(self):
        """
        Subscribe to position updates.
        
        url: user/syncRequest
        """
        if not self.ws:
            print("Not connected")
            return
        
        msg = {
            "url": "user/syncRequest",
            "body": {
                "accounts": [self.auth.account_id]
            }
        }
        
        await self.ws.send(json.dumps(msg))
        print("Subscribed to position updates")
    
    async def _listener(self):
        """Background listener for WS messages"""
        while self.connected and self.ws:
            try:
                msg = await self.ws.recv()
                data = json.loads(msg)
                await self._handle_message(data)
            except websockets.exceptions.ConnectionClosed:
                print("WS connection closed")
                self.connected = False
                break
            except Exception as e:
                print(f"WS error: {e}")
    
    async def _handle_message(self, data: dict):
        """Route messages to handlers"""
        
        # Quote data
        if "quotes" in data.get("d", {}):
            for quote_data in data["d"]["quotes"]:
                quote = Quote(
                    symbol=quote_data.get("contractId"),
                    bid=quote_data.get("bidPrice", 0),
                    ask=quote_data.get("askPrice", 0),
                    last=quote_data.get("price", 0),
                    bid_size=quote_data.get("bidSize", 0),
                    ask_size=quote_data.get("askSize", 0),
                    volume=quote_data.get("volume", 0),
                    timestamp=datetime.now()
                )
                self.quotes[quote.symbol] = quote
                
                for handler in self.quote_handlers:
                    await handler(quote)
        
        # Position data
        if "positions" in data.get("d", {}):
            for pos_data in data["d"]["positions"]:
                if pos_data.get("accountId") == self.auth.account_id:
                    position = Position(
                        symbol=pos_data.get("contractId"),
                        qty=pos_data.get("netPos", 0),
                        avg_entry=pos_data.get("netPrice", 0),
                        unrealized_pnl=pos_data.get("unrealized", 0),
                        timestamp=datetime.now()
                    )
                    self.positions[position.symbol] = position
                    
                    for handler in self.position_handlers:
                        await handler(position)
    
    def on_quote(self, handler: Callable):
        """Register quote handler"""
        self.quote_handlers.append(handler)
    
    def on_position(self, handler: Callable):
        """Register position handler"""
        self.position_handlers.append(handler)
    
    def get_last_quote(self, symbol: str) -> Optional[Quote]:
        """Get last quote for symbol"""
        return self.quotes.get(symbol)
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for symbol"""
        return self.positions.get(symbol)
    
    async def disconnect(self):
        """Close connection"""
        if self.ws:
            await self.ws.close()
            self.connected = False


# Test
async def test_ws():
    import sys
    sys.path.insert(0, '..')
    
    from utils.auth_manager import TradovateAuth
    
    auth = TradovateAuth()
    await auth.authenticate()
    
    client = MarketDataClient(auth)
    
    # Connect
    connected = await client.connect()
    if not connected:
        return
    
    # Subscribe
    await client.subscribe_quote("MNQH6")
    await client.subscribe_position()
    
    # Handler
    async def on_quote(q):
        print(f"Quote: {q.symbol} | Bid: {q.bid} | Ask: {q.ask} | Last: {q.last}")
    
    client.on_quote(on_quote)
    
    # Keep alive
    await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(test_ws())
