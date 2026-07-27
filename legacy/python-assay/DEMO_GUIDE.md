# Crude Assay – Demo Guide

**App URL:** http://localhost:8888 (or http://127.0.0.1:8888) 
**Port:** 8888

---

## Verify it works

From the project root, run:

```bash
uv run python scripts/verify_routes.py
```

This hits the main routes (home, redirects, market, compatibility, dashboard, blending, static) and reports what actually works. If anything fails, you’ll see a list of issues.

**Then run the app and open in a browser:**

```bash
uv run python app.py
```

Open http://localhost:8888/ and use the nav: **Home** | **Dashboard** | **Market** | **Blending** | **Compatibility**.

---

## Quick demo (2–3 minutes)

### 1. Home (single landing)
**URL:** http://localhost:8888/

- One home page: cards for Dashboard, Market, and Compatibility.
- `/assay/` and `/crude-assay/` redirect here.

### 2. Dashboard
**URL:** http://localhost:8888/assay/dashboard

- Quality metrics, API gravity, sulfur, regression, top performers.
- Data from `CrudeAssayService.get_dashboard_data()`.

### 3. Market
**URL:** http://localhost:8888/assay/market

- **Live data only:** WTI and Brent when the market source (Yahoo Finance) returns data.
- If you see *“Live market data (WTI, Brent) is temporarily unavailable”*, the data source didn’t return prices (common on some networks or when Yahoo throttles). The route is working; only the feed is empty.

### 4. Compatibility
**URL:** http://localhost:8888/assay/compatibility

- SBN/IN solvency margin, R, compatibility bands (MFCCT-style).
- Also in the top nav and on the home page as **Compatibility**.

### 5. Blending
**URL:** http://localhost:8888/assay/blending

- Pipeline blending (target volume, API, sulfur) and optional Sunco/refinery models.

### 6. API
**Health (no auth):**
```bash
curl http://localhost:8888/health
curl http://localhost:8888/api/v1/assay/health
```

**Market data (with auth):**
```bash
curl -H "Authorization: Bearer trader-token" \
 http://localhost:8888/api/v1/assay/market-data
```

---

## Talking points

- Crude assay only: no trading, finance, or other workflows.
- **Single home** at `/`; Dashboard, Market, Blending, Compatibility in the nav.
- **Market:** real prices only (WTI/Brent when available); otherwise a clear “temporarily unavailable” message.
- **Compatibility:** SBN/IN, P-Values, BCI and blend risk.
- Run: `uv run python app.py`.
