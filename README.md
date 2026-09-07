# AIPunarartha: Revenue Recovery Engine - Razorpay Buildathon'26

**Punarartha** (punar = again, artha = wealth) = **wealth regained** — a small system that watches failed payments, works out *why* each one failed, and decides a safe, explainable recovery action to get back money that was lost.

---

## Key Features

### Hybrid Classification
- **Rule-Based Mapping**: Maps gateway decline codes directly to standardized buckets (`insufficient_funds`, `card_expired`, `bank_timeout`, `3ds_failed`, `generic_decline`).
- **Indic LLM Fallback**: Leverages Sarvam AI for unstructured failure reasons and natural-language bank responses.

### Deterministic Decision Engine
- **Policy-Driven Actions**: Evaluates failure bucket and customer history to trigger `retry_link`, `reminder`, `escalate`, or `no_action`.
- **Safety & Stopping Rules**: Enforces retry caps, cooldown periods, minimum recoverable amounts, and opt-out suppression.

### Operational Governance
- **Autonomous & Review Queues**: Supports automatic execution (`AUTO_EXECUTE=true`) or manual human approval workflows.
- **Audit Trails & Drift Detection**: Full auditable history for every decision and automated statistical drift monitoring across failure buckets.
- **Keyless Sandbox**: Fully exercisable with zero external credentials using simulated gateways and fallback templates.

---

## Architecture & How It Works

1. **Ingest**: Payment failure arrives via Razorpay webhook or manual API test payload.
2. **Classify**: Deterministic rule classifier identifies failure bucket; uncaught descriptions route to Sarvam AI.
3. **Decide**: Engine applies stopping rules (retry budget, cooldowns, opt-outs) and selects recovery action.
4. **Act**: Either dispatches immediately or holds in the human review queue.
5. **Audit**: Ingest, classification, decision, and outcome logged immutably to SQLite.

```
 [Payment Gateway / Webhook]
             |
             v
     [Ingest & Rate Limiter]
             |
             v
      [Classifier Engine] <---> [Sarvam AI / Rule Engine]
             |
             v
    [Decision Engine]     <---> [Action Rules & Stopping Rules]
             |
      +------+------+
      |             |
      v             v
[Auto-Execution]  [Review Queue]
      |             |
      +------+------+
             |
             v
      [Audit Logging & Outcomes]
```



---

## Installation & Setup

### Prerequisites
- Python 3.13+ and [uv](https://docs.astral.sh/uv/)

### Setup Steps

```bash
# 1. Create virtual environment
uv venv --python 3.13

# 2. Install dependencies
uv pip install -r requirements.txt

# 3. Environment configuration (runs keyless in sandbox mode)
cp .env.example .env
```

### Running the Application

```bash
# 1. Generate synthetic failure events
python -m core.scripts.generate_synthetic_batch

# 2. Classify, decide, and execute
python -m core.scripts.run_pipeline

# 3. Simulate recovery outcomes
python -m core.scripts.simulate_outcomes

# 4. Start the FastAPI backend
python -m uvicorn core.main:app --reload --port 8000

# 5. Start the Streamlit dashboard in another terminal
streamlit run app.py
```

Or on Windows, double-click `start.bat` to launch both services together.

- Dashboard: **http://localhost:8501**
- API Docs: **http://localhost:8000/docs**

---

## Security & Governance Notes

- **Bounded Retries & Cooldowns**: Per-bucket and global caps prevent over-contacting customers.
- **Opt-Out Compliance**: Opted-out customers are permanently excluded from recovery outreach.
- **PII Masking**: Customer phone and email are masked across all UI views and logs.
- **Rate Limiting**: Per-IP limiter protects webhook ingest endpoints against abuse.
- **Graceful Degradation**: System degrades safely to fallbacks if payment gateways or LLMs are unreachable.

---

*Fintech Revenue Recovery & Decision Governance*

