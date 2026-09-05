# AIPunarartha

**Wealth regained** — a small system that watches failed payments, works out *why* each one failed, and decides a safe, explainable recovery action for it. Built around the "revenue recovery" track of an Indian fintech payments hackathon.

**Quickstart:** double-click `start.bat` on Windows (or follow the steps below). The app runs fully even when `.env` has no API keys.

---

## Setup & running

**Prerequisites:** Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
# 1. create the virtual environment (uv downloads Python automatically)
uv venv --python 3.13

# 2. install dependencies
uv pip install -r requirements.txt

# 3. environment file (keys are optional - the app runs keyless)
cp .env.example .env
```

`.env` stays git-ignored. The important values:

| Key | Meaning |
| :--- | :--- |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | Razorpay gateway (test mode). Leave empty for sandbox mode |
| `RAZORPAY_WEBHOOK_SECRET` | signs webhook payloads; if set, unsigned calls are rejected |
| `SARVAM_API_KEY` | Sarvam AI model key. Leave empty for template fallbacks |
| `AUTO_EXECUTE` | `true` = act automatically, `false` = human approval queue |
| `SIMULATION_SEED` | makes outcome simulation reproducible |

**Run it** — from the repo root:

```bash
# 1. generate a synthetic batch of failure events
python -m core.scripts.generate_synthetic_batch

# 2. classify -> decide -> execute over everything unprocessed
python -m core.scripts.run_pipeline

# 3. simulate recovery outcomes (bounded, seeded)
python -m core.scripts.simulate_outcomes

# 4. start the API
python -m uvicorn core.main:app --reload --port 8000

# 5. in another terminal, start the dashboard
streamlit run app.py
```

Or, on Windows, just double-click `start.bat` — it launches the API and the
dashboard together. The dashboard reads the API at `http://localhost:8000`; the
live webhook endpoint is `POST /api/events/webhook/razorpay` (test payloads can
go to `POST /api/events/manual`).

---

## How it works

1. A payment fails. We get the event via a **Razorpay** webhook (or a manual test payload).
2. A **rule classifier** maps the gateway failure code to a bucket — `insufficient_funds`, `card_expired`, `bank_timeout`, `3ds_failed`, `generic_decline`. Anything the rules do not catch goes to the **Sarvam AI** model, which returns a bucket plus a confidence score.
3. A **deterministic decision engine** turns bucket + history into one of `retry_link`, `reminder`, `escalate` or `no_action`. It never improvises — it reads versioned rule files and applies stopping rules (retry caps, a cooldown window, a minimum amount, and customer opt-out). Recovery payment links are created through **Razorpay** when keys are configured.
4. If action is warranted, it either fires automatically (`AUTO_EXECUTE=true`) or lands in a **review queue** for a human to approve.
5. Every step — ingest, classify, decide, act, outcome — is written to an audit log, so any decision can be traced back to the rule (or model output) that produced it.

**Runs without API keys.** The default `.env` has no keys and everything still works:

- No Razorpay keys → keyless sandbox: decisions and drafted messages, no real gateway call or payment link.
- No Sarvam AI key → rule + `ambiguous` classification and fixed English/Hinglish templates.
- No webhook secret → signature checks are skipped (the endpoint stays deduped and rate-limited).

**The dashboard.** A single dark-theme Streamlit app reads the same database: Home, Batch Summary (KPI cards, charts, drift scan), Records (filterable, PII masked), Record Detail (full classify → decide → act chain), Review Queue (human approvals), and Exceptions (manual triage).

---

## Staying safe

- **Small by design.** Not a card processor, not an agent, not a trained model — just a decision system reading two versioned JSON rule files plus an optional, cached, circuit-broken AI call.
- **Bounded retries.** Per-bucket and global caps are enforced across *all* failures of the same order, so a repeat offender keeps losing budget until the engine goes quiet.
- **Cooldowns and minimums.** A dunning cooldown pauses contact after the last attempt; tiny transactions are not chased.
- **Opt-out respected.** An opted-out customer never receives a recovery action.
- **Human gate.** With `AUTO_EXECUTE=false`, nothing is sent until an operator approves it from the dashboard.
- **Degrades, never crashes.** Provider failures fall back gracefully — a 55/55 batch completed even with the AI failing every call.
- **Input hygiene and PII.** Amounts are validated, free text is cleaned, and phone/email are masked everywhere except action execution.
- **Rate limited.** A per-IP limiter guards the ingest endpoints, so bogus events cannot rack up AI calls or fill the database.
- **Observable.** Rotating logs under `logs/`, an audit trail for every decision, and a dashboard drift scan that warns when a failure bucket shifts beyond a threshold.
- **Honest numbers.** Recovered amounts on the dashboard are simulated probabilities, not settlements.
- **Known limits.** Single-user prototype, SQLite storage, drift reporting only (no alerting), and manual live-webhook registration.
- **Credits.** Original code, generated data, and rules. The only external integrations are **Razorpay** (payment gateway/webhooks) and **Sarvam AI** (Indic-language model) — both optional and both fully working in sandbox/fallback mode when no keys are present.