# PSA 10 Scout 🃏

Automated deal-scouting system for PSA 10 graded Pokémon cards.

Monitors eBay listings every few minutes, computes fair market value from
90-day sold comps, scores each listing on a 0–100 deal scale, and sends
instant Telegram alerts when a card is selling below market.

---

## How it works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Price Oracle   │────▶│ Listing Scout   │────▶│  Deal Ranker    │
│                 │     │                 │     │                 │
│ eBay sold comps │     │ Active listings │     │ Score 0–100     │
│ → FMV (90d avg) │     │ vs watchlist    │     │ Save to DB      │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                                              ┌───────────▼──────────┐
                                              │   Telegram Alerts    │
                                              │   Dashboard API      │
                                              └──────────────────────┘
```

**Price Oracle** — queries eBay completed listings for each watchlist card
and computes a weighted FMV (recent sales weighted higher).

**Listing Scout** — scans active eBay listings for each card every N minutes,
comparing ask price against the FMV baseline.

**Deal Ranker** — scores qualifying listings (0–100) based on discount %,
card value tier, and liquidity. Saves deals to SQLite.

**Telegram Bot** — fires an instant alert for every qualifying deal,
plus a daily morning summary.

**Dashboard API** — Flask endpoint serving deal data to the React frontend.

---

## Quick start

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/psa10-scout.git
cd psa10-scout

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Open .env and fill in your API keys (see setup guides below)
```

### 3. Edit your watchlist

Open `data/watchlist.json` and add or remove cards you want to track.
Each entry needs a `name` (used as the eBay search query) and a `set`.

### 4. Run

```bash
python main.py
```

The scout runs immediately on startup, then repeats every `SCOUT_INTERVAL_MINUTES`.
Logs go to the terminal and to `logs/scout.log`.

---

## API key setup

### eBay Developer Account (free)

1. Go to [developer.ebay.com](https://developer.ebay.com) and register
2. Create a new application
3. Copy your **App ID (Client ID)** → paste as `EBAY_APP_ID` in `.env`
4. The Finding API only needs the App ID — no OAuth required for read-only searches

### Telegram Bot (free, ~5 minutes)

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`, follow prompts, copy the token → `TELEGRAM_BOT_TOKEN`
3. Send any message to your new bot
4. Run `python scripts/get_chat_id.py` → copy output → `TELEGRAM_CHAT_ID`

---

## Project structure

```
psa10-scout/
├── agents/
│   ├── price_oracle.py       # fetches eBay sold comps → computes FMV
│   ├── listing_scout.py      # scans active listings vs watchlist
│   └── deal_ranker.py        # scores deals, persists to DB
├── core/
│   ├── config.py             # all settings loaded from .env
│   ├── database.py           # SQLite schema + CRUD helpers
│   └── models.py             # Card, Listing, Deal dataclasses
├── alerts/
│   └── telegram_bot.py       # instant deal alerts + daily summary
├── dashboard/
│   └── app.py                # Flask API → GET /api/deals
├── data/
│   ├── watchlist.json        # cards to track (edit this)
│   └── watchlist.py          # loader + key normaliser
├── scripts/
│   └── get_chat_id.py        # Telegram setup helper
├── tests/
│   └── test_deal_ranker.py   # unit tests for scoring logic
├── logs/                     # auto-created on first run
├── main.py                   # scheduler entry point
├── requirements.txt
├── .env.example              # copy to .env and fill in keys
└── .gitignore
```

---

## Configuration reference

| Variable | Default | Description |
|---|---|---|
| `EBAY_APP_ID` | — | eBay developer App ID (required) |
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token (required for alerts) |
| `TELEGRAM_CHAT_ID` | — | Your Telegram chat ID (required for alerts) |
| `DEAL_DISCOUNT_THRESHOLD` | `0.10` | Minimum discount to flag as a deal (10%) |
| `FIRE_DEAL_THRESHOLD` | `0.25` | Threshold for "fire deal" badge (25%) |
| `SCOUT_INTERVAL_MINUTES` | `5` | How often to scan listings |
| `FMV_LOOKBACK_DAYS` | `90` | Days of sold history used for FMV |
| `DB_PATH` | `data/psa10_scout.db` | SQLite database path |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG / INFO / WARNING) |

---

## Deal scoring model

Each qualifying listing is scored 0–100:

| Component | Max pts | Logic |
|---|---|---|
| Discount % | 60 | Scaled from threshold to 2× fire deal threshold |
| Card value tier | 20 | Higher FMV cards score higher (more upside) |
| Liquidity | 20 | Placeholder — PSA pop report integration planned |

A score ≥ 80 is a strong deal. Fire deals (>25% off) will typically score 70+.

---

## Running the dashboard API

```bash
python dashboard/app.py
```

Endpoints:
- `GET /api/deals` — returns recent deals (params: `limit`, `min_score`, `fire_only`)
- `GET /api/health` — health check

---

## Running tests

```bash
python -m pytest tests/
# or directly:
python tests/test_deal_ranker.py
```

---

## Roadmap

- [ ] TCGPlayer price feed integration
- [ ] PSA Pop Report scraper for rarity scoring
- [ ] Price trend detection (rising / falling)
- [ ] React frontend wired to live `/api/deals`
- [ ] Mercari listing support
- [ ] Docker + cron deployment config
- [ ] Email digest as alternative to Telegram
