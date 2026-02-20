#!/usr/bin/env python3
"""
MNQ 30 Point Momentum Strategy
Trigger: 5-minute candle CLOSES with 30pt move (not wicks)
Entry: Market order immediately
Stop: LOW of breakout candle
Target: 1R exactly (data shows TP1 = best)
NO trailing stop
"""

from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Candle:
    """5-minute candle data"""
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        return self.close < self.open


class Momentum30pt:
    """
    Strategy: 30 Point Momentum on 5-Min CLOSES
    
    Rules:
    1. Trigger: 5min candle closes with 30pt+ move from prior close
    2. Entry: Market order immediately on candle close
    3. Stop: LOW of breakout candle (NOT swing low)
    4. Target: 1R exactly (data shows TP1 is best)
    5. NO trailing stop - set and forget
    
    Key: Uses CLOSE price, not wicks.
    """
    
    def __init__(self):
        self.candles: list[Candle] = []
        self.trigger_threshold = 30  # points
        self.current_signal = None
        
    def on_candle_close(self, candle: Candle) -> Optional[Dict]:
        """
        Process complete 5min candle.
        
        Returns signal dict if 30pt+ move detected.
        """
        self.candles.append(candle)
        
        # Need at least 2 candles
        if len(self.candles) < 2:
            return None
        
        breakout_candle = candle
        prior_candle = self.candles[-2]
        
        # Calculate move from prior CLOSE to current CLOSE
        move = breakout_candle.close - prior_candle.close
        
        # Check 30pt threshold
        if abs(move) >= self.trigger_threshold:
            direction = "Buy" if move > 0 else "Sell"
            
            # Stop at LOW of breakout candle
            stop = breakout_candle.low if direction == "Buy" else breakout_candle.high
            
            signal = {
                "direction": direction,
                "entry_price": breakout_candle.close,
                "stop_price": stop,
                "breakout_candle": breakout_candle,
                "prior_candle": prior_candle,
                "move_points": abs(move),
                "risk_points": abs(breakout_candle.close - stop),
                "timestamp": breakout_candle.timestamp
            }
            
            self.current_signal = signal
            return signal
        
        return None
    
    def calculate_target(self, entry: float, stop: float, direction: str) -> float:
        """
        Calculate 1R profit target.
        
        R = |entry - stop|
        Target = entry + R (BUY) or entry - R (SELL)
        """
        risk = abs(entry - stop)
        
        if direction == "Buy":
            return entry + risk
        else:
            return entry - risk
    
    def print_signal(self, signal: Dict) -> str:
        """Pretty print signal details"""
        return f"""
🎯 30PT MOMENTUM SIGNAL
   Direction: {signal['direction']}
   Entry: {signal['entry_price']:.2f}
   Stop: {signal['stop_price']:.2f} (low of breakout candle)
   Risk: ${signal['risk_points'] * 0.50:.2f} ({signal['risk_points']:.0f} pts)
   Target: {self.calculate_target(signal['entry_price'], signal['stop_price'], signal['direction']):.2f} (1R)
   Move: {signal['move_points']:.0f} pts
   Type: Set and forget, TP at 1R
        """


# Test
if __name__ == "__main__":
    strategy = Momentum30pt()
    
    # Simulate candles
    from datetime import datetime, timedelta
    
    base_time = datetime.now()
    
    # Create test candles
    candles = [
        Candle(20500, 20520, 20490, 20510, 1000, base_time),
        Candle(20510, 20535, 20500, 20535, 1200, base_time + timedelta(minutes=5)),  # +25pt (no signal)
        Candle(20535, 20545, 20505, 20545, 1100, base_time + timedelta(minutes=10)), # +30pt (signal!)
        Candle(20545, 20550, 20530, 20530, 900, base_time + timedelta(minutes=15)),  # -15pt (no signal)
    ]
    
    for c in candles:
        signal = strategy.on_candle_close(c)
        if signal:
            print(strategy.print_signal(signal))
