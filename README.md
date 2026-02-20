# Wolf MNQ Trading Bot

⚠️ **ALWAYS START WITH DEMO MODE** — Paper trade first, validate edge, then go live.

AI-powered bot for trading MNQ (Micro Nasdaq) futures on Tradovate.

## Quick Start (Demo Mode)

```bash
# 1. Clone repository
git clone https://github.com/buttenhook/mnq-bot.git
cd mnq-bot

# 2. Set credentials
cp config/.env.example .env
nano .env  # Add your demo credentials

# 3. Run paper trading
export TRADOVATE_MODE=demo
python3 main.py
```

See [SETUP.md](SETUP.md) for detailed instructions.

---

## Strategy: 30 Point Momentum

**Trigger:** 5-minute candle CLOSES with 30+ point move from prior close  
**Entry:** Market order immediately on candle close  
**Stop Loss:** LOW of the breakout candle (prior 5min)  
**Target:** Exactly 1R — data shows this is optimal  
**Trailing:** **NONE** — set and forget

### Why 1R?
Backtest data shows taking TP1 at 1R outperforms the "let it ride" approach.

### Why Candle Low?
Stop at the LOW of the breakout candle, not swing lows. This gives a tighter stop while respecting the momentum.

### Rules Summary
1. Candle must **CLOSE** 30+ points from prior candle's close
2. Use the **CLOSE**, not wicks
3. Stop at candle **LOW** (longs) or **HIGH** (shorts)
4. Target at **1R exactly** (not 2R)
5. **No trailing** — let the trade play out

---

## Repository Structure

```
mnq-bot/
├── main.py                    # Main bot loop
├── SETUP.md                   # Detailed setup guide
├── config/
│   └── .env.example          # Credentials template
├── core/                      # Core components
│   ├── auth_manager.py       # Token auth + renewal
│   ├── order_manager.py      # Place/cancel orders (REST)
│   ├── market_data.py        # WebSocket quotes + positions
│   └── risk_manager.py       # Position sizing, kill switch
├── strategies/
│   └── momentum_30pt.py      # 30pt strategy logic
└── utils/
    └── auth_manager.py       # (duplicate, use core/)
```

---

## Demo Mode vs Live

| Feature | Demo (Paper) | Live (Real Money) |
|---------|--------------|-------------------|
| Money | Simulated | Real $500+ |
| Risk | None | Real P&L |
| API | demo.tradovateapi.com | live.tradovateapi.com |
| WebSocket | md.tradovateapi.com | md.tradovateapi.com |
| Fills | Simulated delay | Real market liquidity |
| **START HERE** | ✅ This first | Only after demo works |

---

## Process

### Phase 1: Demo (Paper Trading)
1. Create demo account
2. Run bot for 2-4 weeks
3. Log every trade to `paper_trades.log`
4. Analyze win rate, R-multiples
5. Validate edge exists

### Phase 2: Live (Real Money)
1. Fund account ($500 minimum)
2. Switch to `TRADOVATE_MODE=live`
3. Trade with 1 MNQ contract
4. Same strategy, same risk rules
5. Scale up gradually

---

## Key Technical Details

### API Endpoints
- **Auth:** `POST /auth/accessTokenRequest`
- **Order:** `POST /order/placeorder`
- **WebSocket:** `wss://md.tradovateapi.com/v1/websocket`

### MNQ Contract
- Symbol: `MNQH6` (March expiry)
- Tick value: $0.50 per 0.25 points
- 24/5 market

### Timeframes
- Token expiry: 90 minutes
- Renew at: 75 minutes
- Candle close: Every 5 minutes
- Max sessions: 2 concurrent

---

## Risk Management

Built-in safeguards:
- ❌ Max daily loss: -$500 (stops all trading)
- ❌ Max position: 1 MNQ
- ❌ Kill switch: Emergency flatten
- ✅ Paper mode: Zero financial risk

---

## Documentation

- **SETUP.md** — Step-by-step setup guide
- This README — Quick reference
- Inline comments — Strategy logic

---

**Bot Status:** Demo mode ready 🐺
