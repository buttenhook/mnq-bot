# MNQ Bot Setup Guide

## Phase 1: Demo Mode (Paper Trading)
**START HERE** — Practice with simulated money first.

### 1. Create Tradovate Account
- Go to: https://tradovate.com
- Open account → Select "Demo" (simulated)
- No funding required
- Get username/password

### 2. Enable API Access
- Login to Tradovate
- Settings → API Access
- Generate API Key + Secret
- Save both securely

### 3. Configure Bot
```bash
cd mnq-bot
cp config/.env.example .env
nano .env
```

Add credentials:
```bash
TRADOVATE_USERNAME=your_username
TRADOVATE_PASSWORD=your_password
TRADOVATE_API_SECRET=your_secret_here
TRADOVATE_ACCOUNT_ID=your_demo_account_id
```

### 4. Run Demo Mode
```bash
export TRADOVATE_MODE=demo
python3 main.py
```

**Expected output:**
```
🐺 Wolf MNQ Bot initialized
Mode: PAPER
Strategy: 30pt momentum (5min CLOSES)
Stop: Candle LOW | Target: 1R | NO trail

5min candle closed...
[5min CLOSE] O:20500 H:20540 L:20490 C:20535
30pt detected!
🔵 PAPER TRADE LOGGED
```

### 5. Paper Trade for 2-4 Weeks
- Validate strategy edge
- Check win rate
- Log P&L
- Look for patterns

---

## Phase 2: Live Trading

### When Ready:
1. Fund account ($500+ recommended)
2. Switch to live endpoints
3. Deploy with 1 MNQ contract

### Switch to Live
```bash
# Set live mode
export TRADOVATE_MODE=live

# Run
python3 main.py
```

**Live mode:**
- Real money at risk
- Real fills
- Same strategy, same risk rules

---

## Important Notes

### Demo vs Live
| Feature | Demo | Live |
|---------|------|------|
| Money | Simulated | Real |
| API | demo.tradovateapi.com | live.tradovateapi.com |
| WebSocket | Same: md.tradovateapi.com | Same: md.tradovateapi.com |
| Fills | Simulated delay | Real market |

### Strategy Rules
✅ **30pt move** on 5min CLOSE (not wick)
✅ Stop at **LOW of breakout candle**
✅ Target at **1R exactly** (data proven)
✅ **NO trailing stops** — set and forget

### Symbol Format
- March expiry: `MNQH6`
- $0.50 per tick (0.25 points)
- Update symbol in main.py if expired

---

## Troubleshooting

### "Authentication failed"
- Check username/password
- Verify API secret
- Ensure account is funded (even demo needs $0 balance check)

### "WebSocket disconnected"
- Normal — will auto-reconnect
- Check internet connection
- Verify token not expired

### No signals
- 30pt moves are rare
- Check market hours (MNQ = 24/5)
- Verify quotes are coming through

---

## Stats Tracking

Paper trades logged to: `paper_trades.log`

Example:
```json
{"time": "2026-02-20T09:30:00", "symbol": "MNQH6", "direction": "Buy", "entry": 20500, "stop": 20470, "target": 20530, "risk": 30, "mode": "PAPER"}
```

---

**Ready to start?** Phase 1: Demo mode. Don't skip it.
