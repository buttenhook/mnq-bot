#!/usr/bin/env python3
"""
Tradovate Order Manager
Handles: placing, modifying, cancelling, tracking orders
"""

import aiohttp
import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class OrderAction(Enum):
    BUY = "Buy"
    SELL = "Sell"


class OrderType(Enum):
    MARKET = "Market"
    LIMIT = "Limit"
    STOP = "Stop"
    STOP_LIMIT = "StopLimit"


class TimeInForce(Enum):
    DAY = "Day"
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill


@dataclass
class Order:
    order_id: Optional[int]
    symbol: str
    action: OrderAction
    qty: int
    order_type: OrderType
    price: Optional[float]
    stop_price: Optional[float]
    time_in_force: TimeInForce
    status: str = "Pending"
    filled_qty: int = 0
    avg_price: float = 0.0
    is_automated: bool = True


class OrderManager:
    """
    Manages order lifecycle.
    
    Endpoints:
    - POST /order/placeorder
    - POST /order/cancelorder
    - POST /order/modifyorder
    - GET /order/list
    """
    
    def __init__(self, auth_manager):
        self.auth = auth_manager
        self.base_url = auth_manager.base_url
        self.pending_orders: Dict[int, Order] = {}
        self.executions: list = []
        
    async def place_order(
        self,
        symbol: str,
        action: str,  # "Buy" or "Sell"
        qty: int,
        order_type: str = "Market",
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "Day"
    ) -> Optional[Dict]:
        """
        Place an order.
        
        Returns: { "orderId": 1234567 } or None on failure
        """
        url = f"{self.base_url}/order/placeorder"
        headers = self.auth.get_auth_headers()
        
        body = {
            "accountSpec": self.auth.username,
            "accountId": int(self.auth.account_id),
            "action": action,
            "symbol": symbol,
            "orderQty": qty,
            "orderType": order_type,
            "isAutomated": True,
            "timeInForce": time_in_force
        }
        
        # Add price for limit/stop orders
        if price and order_type in ["Limit", "StopLimit"]:
            body["price"] = price
            
        if stop_price and order_type in ["Stop", "StopLimit"]:
            body["stopPrice"] = stop_price
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body) as resp:
                    data = await resp.json()
                    
                    if resp.status == 200:
                        order_id = data.get("orderId")
                        print(f"✅ Order placed: {action} {qty}x {symbol} @ {order_type} | ID: {order_id}")
                        
                        # Track locally
                        order = Order(
                            order_id=order_id,
                            symbol=symbol,
                            action=OrderAction(action),
                            qty=qty,
                            order_type=OrderType(order_type),
                            price=price,
                            stop_price=stop_price,
                            time_in_force=TimeInForce(time_in_force),
                            status="Working"
                        )
                        if order_id:
                            self.pending_orders[order_id] = order
                        
                        return data
                    else:
                        print(f"❌ Order failed: {data}")
                        return None
                        
        except Exception as e:
            print(f"Order error: {e}")
            return None
    
    async def cancel_order(self, order_id: int) -> bool:
        """
        Cancel an existing order.
        
        POST /order/cancelorder
        """
        url = f"{self.base_url}/order/cancelorder"
        headers = self.auth.get_auth_headers()
        
        body = {"orderId": order_id}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body) as resp:
                    if resp.status == 200:
                        print(f"✅ Cancelled order: {order_id}")
                        if order_id in self.pending_orders:
                            self.pending_orders[order_id].status = "Cancelled"
                        return True
                    else:
                        print(f"⚠️ Cancel failed: {resp.status}")
                        return False
        except Exception as e:
            print(f"Cancel error: {e}")
            return False
    
    async def modify_order(
        self,
        order_id: int,
        new_price: Optional[float] = None,
        new_qty: Optional[int] = None
    ) -> bool:
        """
        Modify an existing order.
        
        POST /order/modifyorder
        """
        url = f"{self.base_url}/order/modifyorder"
        headers = self.auth.get_auth_headers()
        
        body = {"orderId": order_id}
        if new_price:
            body["price"] = new_price
        if new_qty:
            body["orderQty"] = new_qty
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body) as resp:
                    if resp.status == 200:
                        print(f"✅ Modified order: {order_id}")
                        return True
                    else:
                        print(f"⚠️ Modify failed: {resp.status}")
                        return False
        except Exception as e:
            print(f"Modify error: {e}")
            return False
    
    async def get_orders(self, status: str = "Working") -> list:
        """
        Get list of orders.
        
        GET /order/list or /order/deps
        """
        url = f"{self.base_url}/order/list"
        headers = self.auth.get_auth_headers()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data
                    return []
        except Exception as e:
            print(f"Get orders error: {e}")
            return []
    
    async def flatten_all(self) -> bool:
        """
        Cancel all working orders (emergency kill switch).
        """
        orders = await self.get_orders("Working")
        for order in orders:
            await self.cancel_order(order.get("orderId"))
        print(f"Flattened {len(orders)} orders")
        return True


# Example usage
async def test_orders():
    from utils.auth_manager import TradovateAuth
    
    auth = TradovateAuth()
    await auth.authenticate()
    
    manager = OrderManager(auth)
    
    # Paper order
    result = await manager.place_order(
        symbol="MNQH6",
        action="Buy",
        qty=1,
        order_type="Market"
    )
    
    print(result)


if __name__ == "__main__":
    asyncio.run(test_orders())
