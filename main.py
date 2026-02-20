#!/usr/bin/env python3
"""
Wolf MNQ Trading Bot
Paper → Live mode with 30pt momentum strategy

Strategy:
- 5min candle closes 30pt+ from prior close
- Entry immediately on close
- Stop: LOW of breakout candle
- Target: 1R exactly
- NO trailing stop
"""

import asyncio
import signal
from datetime import datetime
from typing import Optional

from utils.auth_manager import TradovateAuth
from core.order_manager import OrderManager
from core.market_data import MarketDataClient, Quote
from core.risk_manager import RiskManager, RiskConfig
from strategies.momentum_30pt import Momentum30pt, Candle


class MNQTradingBot:
    """
    Main trading bot coordinator.
    
    Flow:
    1. Authenticate with Tradovate
    2. Connect to market data (WebSocket)
    3. Build 5-min candles from ticks
    4. Detect 30pt momentum on CLOSE
    5. Execute: Stop at candle LOW, Target at 1R
    6. Set and forget - no trailing
    """
    
    def __init__(self, paper_mode: bool = True, symbol: str = "MNQH6"):
        self.symbol = symbol
        self.paper_mode = paper_mode
        
        # Components
        self.auth: Optional[TradovateAuth] = None
        self.orders: Optional[OrderManager] = None
        self.market_data: Optional[MarketDataClient] = None
        self.risk: Optional[RiskManager] = None
        self.strategy: Optional[Momentum30pt] = None
        
        # State
        self.running = False
        self.current_candle: Optional[Candle] = None
        self.last_signal: Optional[dict] = None
        
        # Stats
        self.trades_today = 0
        self.daily_pnl = 0.0
        
        print(f"🐺 Wolf MNQ Bot initialized")
        print(f"   Mode: {'PAPER' if paper_mode else 'LIVE'}")
        print(f"   Symbol: {symbol}")
        print(f"   Strategy: 30pt momentum (5min CLOSES)")
        print(f"   Stop: Candle LOW | Target: 1R | NO trail")
        
    async def start(self):
        """Start the bot"""
        print("\n" + "="*60)
        print("STARTING BOT")
        print("="*60)
        
        # 1. Authenticate
        self.auth = TradovateAuth()
        success = await self.auth.authenticate()
        if not success:
            print("❌ Authentication failed")
            return
        
        # 2. Initialize components
        self.orders = OrderManager(self.auth)
        self.market_data = MarketDataClient(self.auth)
        self.risk = RiskManager(RiskConfig(
            max_daily_loss=-500,
            account_balance=5000,
            r_per_trade=100  # $100 risk per trade
        ))
        self.strategy = Momentum30pt()
        
        # 3. Connect to market data
        ws_connected = await self.market_data.connect()
        if ws_connected:
            await self.market_data.subscribe_quote(self.symbol)
            await self.market_data.subscribe_position()
            self.market_data.on_quote(self._on_quote)
            
        # 4. Start main loop
        self.running = True
        asyncio.create_task(self.auth.auto_renew())
        asyncio.create_task(self._candle_builder())
        
        print("\n✅ Bot running. Press Ctrl+C to stop.")
        
        while self.running:
            await asyncio.sleep(1)
    
    def _on_quote(self, quote: Quote):
        """Handle real-time quote, build candle"""
        if not self.current_candle:
            self.current_candle = Candle(
                open=quote.last,
                high=quote.last,
                low=quote.last,
                close=quote.last,
                volume=quote.volume,
                timestamp=datetime.now()
            )
        else:
            self.current_candle.high = max(self.current_candle.high, quote.last)
            self.current_candle.low = min(self.current_candle.low, quote.last)
            self.current_candle.close = quote.last
            self.current_candle.volume = quote.volume
    
    async def _candle_builder(self):
        """Build 5-minute candles and check for signals"""
        while self.running:
            await asyncio.sleep(300)  # 5 minutes
            
            if not self.current_candle:
                continue
            
            candle = self.current_candle
            self.current_candle = None
            
            print(f"\n[5min CLOSE] O:{candle.open:.2f} H:{candle.high:.2f} L:{candle.low:.2f} C:{candle.close:.2f}")
            
            signal = self.strategy.on_candle_close(candle)
            
            if signal:
                self.last_signal = signal
                print(self.strategy.print_signal(signal))
                await self._execute_signal(signal)
    
    async def _execute_signal(self, signal: dict):
        """Execute trade signal"""
        direction = signal["direction"]
        entry = signal["entry_price"]
        stop = signal["stop_price"]
        target = self.strategy.calculate_target(entry, stop, direction)
        
        # GUARDRAIL: No double positions
        if self.position and self.position.qty != 0:
            print(f"\n🔒 GUARDRAIL: Position already open ({self.position.qty}x). Skip.")
            return
        
        # Risk check
        
        allowed, reason = self.risk.check_entry(direction, 1, entry, stop)
        
        if not allowed:
            print(f"❌ Risk block: {reason}")
            return
        
        print(f"\n🎯 EXECUTING:")
        print(f"   {direction} 1x {self.symbol}")
        print(f"   Entry: {entry:.2f}")
        print(f"   Stop: {stop:.2f} (low of breakout candle)")
        print(f"   Target: {target:.2f} (1R = ${abs(entry-stop)*0.50:.2f})")
        print(f"   Set and forget - no trailing stop")
        
        if self.paper_mode:
            await self._paper_trade(signal, target)
        else:
            await self._live_trade(signal, target)
    
    async def _paper_trade(self, signal: dict, target: float):
        """Log paper trade"""
        trade = {
            "time": datetime.now().isoformat(),
            "symbol": self.symbol,
            "direction": signal["direction"],
            "entry": signal["entry_price"],
            "stop": signal["stop_price"],
            "target": target,
            "risk": signal["risk_points"],
            "mode": "PAPER"
        }
        
        with open("paper_trades.log", "a") as f:
            f.write(f"{trade}\n")
        
        print(f"   🔵 PAPER TRADE LOGGED")
        self.risk.record_trade()
        self.trades_today += 1
    
    async def _live_trade(self, signal: dict, target: float):
        """Execute live trade"""
        direction = signal["direction"]
        
        # Entry market order
        result = await self.orders.place_order(
            symbol=self.symbol,
            action=direction,
            qty=1,
            order_type="Market"
        )
        
        if result:
            print(f"   🔴 LIVE ENTRY FILLED")
            
            # Stop order
            await self.orders.place_order(
                symbol=self.symbol,
                action="Sell" if direction == "Buy" else "Buy",
                qty=1,
                order_type="Stop",
                stop_price=signal["stop_price"]
            )
            print(f"   🛑 Stop placed at {signal['stop_price']}")
            
            # Target order (1R)
            await self.orders.place_order(
                symbol=self.symbol,
                action="Sell" if direction == "Buy" else "Buy",
                qty=1,
                order_type="Limit",
                price=target
            )
            print(f"   🎯 Target placed at {target} (1R)")
            
            self.risk.record_trade()
            self.trades_today += 1
    
    async def stop(self):
        """Stop bot gracefully"""
        print("\n🛑 Stopping bot...")
        self.running = False
        
        if self.orders:
            print("   Flattening positions...")
            await self.orders.flatten_all()
        
        if self.market_data:
            await self.market_data.disconnect()
        
        print("Bot stopped.")
        print(f"Trades today: {self.trades_today}")
        print(f"Daily P&L: ${self.daily_pnl:.2f}")


async def main():
    import os
    paper = os.getenv("TRADOVATE_MODE", "demo") == "demo"
    bot = MNQTradingBot(paper_mode=paper)
    
    def shutdown(sig, frame):
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, shutdown)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
