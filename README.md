# Wolf MNQ Trading Bot

AI-powered bot for trading MNQ (Micro Nasdaq) futures on Tradovate.

## Strategy: 30 Point Momentum

**Trigger:** 5-minute candle closes with 30+ point move from prior close  
**Entry:** Market order immediately on candle close  
**Stop Loss:** LOW of the breakout candle (prior 5min)  
**Target:** Exactly 1R (data shows TP1 is optimal)  
**Trailing:** NONE - set and forget

### Rules
1. Candle must CLOSE 30+ points from prior candle's close
2. Use the candle CLOSE, not the wick
3. Stop at candle LOW for longs, HIGH for shorts
4. Target at 1R exactly (not 2R)
5. No trailing - let trade play out

## Setup

### 1. Get Tradovate API Credentials
- Create account at tradovate.com
- Fund with $500+
- Enable API access in settings
- Get: username, password, API secret

### 2. Set Environment Variables
```bash
# Create .env file
cp config/.env.example .env

# Edit with your credentials
nano .env

# Add:
TRADOVATE_USERNAME=your_username
TRADOVATE_PASSWORD=your_password
TRADOVATE_API_SECRET=your_secret_here
TRADOVATE_ACCOUNT_ID=your_account_id
```

### 3. Install Dependencies
```bash
pip install aiohttp websockets
```

## Running

### Paper Trading (Demo Mode)
```bash
export TRADOVATE_MODE=demo
python3 main.py
```

### Live Trading (Real Money)
```bash
export TRADOVATE_MODE=live
python3 main.py
```

## Files

```
mnq-bot/
├── main.py                 # Main bot
├── config/
│   └── .env.example        # Credentials template
├── utils/
│   └── auth_manager.py     # Token auth + renewal
├── core/
│   ├── order_manager.py    # Place/cancel/modify orders
│   ├── market_data.py      # WebSocket quotes
│   └── risk_manager.py     # Position sizing + killswitch
├── strategies/
│   └── momentum_30pt.py    # Your strategy
└── README.md
```

## Key Technical Details

### API Endpoints
- Auth: `POST /auth/accessTokenRequest`
- Orders: `POST /order/placeorder`
- WebSocket: `wss://md-live.tradovateapi.com/v1/websocket`

### MNQ Contract Format
- March: `MNQH6`
- June: `MNQM6`
- $0.50 per tick (0.25 points)
- Pick symbol based on expiry

### Risk Management
- Max daily loss: -$500
- Max position size: 1 MNQ (configurable)
- Kill switch: auto-flatten on limit hit
- Paper mode: logs trades to `paper_trades.log`

## Process

1. **Paper Trade**: Run 2+ weeks, validate edge
2. **Small Live**: 1 MNQ contracts, $2/point
3. **Scale**: Add size

## Data Shows

- **30pt momentum** triggers on 5min closes
- **1R profit** is optimal (not 2R)
- **Stop at candle LOW** works better than swing lows
- **No trailing** - set and forget

---
*Wolf Trading Bot | Feb 2026*
