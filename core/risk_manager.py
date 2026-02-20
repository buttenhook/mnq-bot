#!/usr/bin/env python3
"""
Tradovate Risk Manager
Handles: daily loss limits, position sizing, kill switch
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta


@dataclass
class RiskConfig:
    """Risk parameters for trading"""
    max_daily_loss: float = -500      # USD, stop trading if hit
    max_position_size: int = 2        # Max contracts
    max_trades_per_day: int = 10      # Max trades
    position_size_pct: float = 0.02    # 2% of account per trade
    account_balance: float = 10000    # Default for sizing
    r_per_trade: float = 100         # 1R = $100 (MNQ ~2 ticks)
    
    @property
    def position_size(self) -> int:
        """Calculate position size in contracts"""
        size = int((self.account_balance * self.position_size_pct) / self.r_per_trade)
        return min(size, self.max_position_size)


class RiskManager:
    """
    Manages trading risk.
    
    Rules:
    - Max daily loss: stop all trading
    - Max positions: no new entries
    - Position sizing: 2% of account
    - Kill switch: emergency flatten
    """
    
    def __init__(self, config: RiskConfig = None):
        self.config = config or RiskConfig()
        
        # Session state
        self.daily_pnl: float = 0.0
        self.trades_today: int = 0
        self.daily_start: datetime = datetime.now()
        self.kill_switch_triggered: bool = False
        
    def check_entry(self, direction: str, size: int, entry_price: float, stop_price: float) -> tuple[bool, str]:
        """
        Check if entry is allowed.
        
        Returns: (allowed: bool, reason: str)
        """
        # Kill switch
        if self.kill_switch_triggered:
            return False, "KILL_SWITCH active"
        
        # Daily loss limit
        if self.daily_pnl <= self.config.max_daily_loss:
            self.kill_switch_triggered = True
            return False, f"DAILY_LOSS hit ({self.daily_pnl})"
        
        # Max trades
        if self.trades_today >= self.config.max_trades_per_day:
            return False, "MAX_TRADES reached"
        
        # Max position size
        if size > self.config.max_position_size:
            return False, f"MAX_SIZE exceeded ({size} > {self.config.max_position_size})"
        
        # Check risk:reward (minimum 1:1)
        risk = abs(entry_price - stop_price)
        # For MNQ, risk in points
        reward_per_contract = risk * 0.50  # $0.50 per point
        
        if reward_per_contract < self.config.r_per_trade:
            return False, f"Poor R:R ({risk} pts = ${reward_per_contract})"
        
        return True, "OK"
    
    def update_pnl(self, realized_pnl: float):
        """Update daily P&L after trade closes"""
        self.daily_pnl += realized_pnl
        print(f"Daily P&L: ${self.daily_pnl:.2f} | Trades: {self.trades_today}")
        
        if self.daily_pnl <= self.config.max_daily_loss:
            print(f"🚨 DAILY LOSS LIMIT HIT: ${self.daily_pnl}")
            self.kill_switch_triggered = True
    
    def record_trade(self):
        """Increment trade counter"""
        self.trades_today += 1
    
    def reset_day(self):
        """Reset for new trading day"""
        if datetime.now().date() > self.daily_start.date():
            self.daily_pnl = 0.0
            self.trades_today = 0
            self.daily_start = datetime.now()
            self.kill_switch_triggered = False
            print("📅 New day reset")
    
    def get_position_size(self) -> int:
        """Get recommended position size"""
        return self.config.position_size
    
    def calculate_stop(self, entry: float, direction: str, atr: float = None) -> float:
        """
        Calculate stop loss.
        
        For MNQ:
        - Default: 30 points (15 ticks) = $15
        - With ATR: 2x ATR
        """
        default_stop = 30  # points
        
        if atr:
            stop = entry - (direction == "Buy" and atr * 2 or -atr * 2)
        else:
            if direction == "Buy":
                stop = entry - default_stop
            else:
                stop = entry + default_stop
        
        return stop
    
    def calculate_target(self, entry: float, direction: str, stop: float, risk: float = None) -> float:
        """
        Calculate profit target.
        
        Minimum 1:2 R:R (reward = 2x risk)
        """
        if risk is None:
            risk = abs(entry - stop)
        
        target_risk = risk * 2  # 2:1 minimum
        
        if direction == "Buy":
            target = entry + target_risk
        else:
            target = entry - target_risk
        
        return target


# Example
if __name__ == "__main__":
    config = RiskConfig(
        max_daily_loss=-300,
        account_balance=5000,
        r_per_trade=50
    )
    
    rm = RiskManager(config)
    
    # Test entry check
    allowed, reason = rm.check_entry("Buy", 1, 20500, 20470)
    print(f"Entry allowed: {allowed} ({reason})")
    
    # Position size
    print(f"Position size: {rm.get_position_size()} contracts")
