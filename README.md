# AIPunarartha

An AI agent that detects revenue at risk from failed payments, classifies why each failure happened, picks the right bounded recovery action, executes it, and logs every single decision to an auditable trail.

---

## Problem

Payment failures silently bleed merchant revenue. A card declines, a bank times out, a 3DS check fails — and the money is just gone. Recovery today is either "do nothing" or unstructured manual follow-up. There's no system watching, deciding, and acting in a bounded, auditable way. Payment gateways move money at the point of sale but don't send reminders, track failures, or manage dunning. That gap is what AIPunarartha fills.

---

## How It Works

```
[Synthetic Batch + Gateway Webhooks] ──> [PaymentEvent table]
                                                  │
                                                  ▼
                                        ┌─ Classifier ─┐
                                        │              │
                              known decline code    free-text / unclear
                              → rule lookup            |
                                        │              │
                                        └──────┬───────┘
                                               ▼
                                     [Decision Engine]
                                     (deterministic, no LLM)
                                               │
                              ┌────────────────┼────────────────┐
                              │                │                │
                         retry_link        reminder         escalate
                              │                │                │
                              ▼                ▼                ▼
                            Payment        AI drafts       logged as
                    Links API (real)    EN + Hinglish     exception /
                                              │           manual review
                                              ▼
                                        [AuditLog]
                                  every step, every actor,
                                  every reasoning string
```

---

## What's Deterministic vs. What's AI

This is the core design rule — non-negotiable:

| Component | Who decides | Why |
|---|---|---|
| **Classification** (known decline codes) | Rules engine (`decline_rules.json`) | Deterministic, inspectable, zero cost |
| **Classification** (ambiguous/free-text) | Indic-language LLM | Only when rules can't match — Hindi/Hinglish input needs LLM understanding |
| **Recovery action** (what to do) | Rules engine (`action_rules.json`) | Deterministic. Never offloaded to the LLM. |
| **Recovery message** (what to say) | Indic-language LLM | Needs natural language, Indic-language fluency — this is where it genuinely shines |

The LLM never chooses the action. It feeds structured output (bucket + confidence) into the rules engine, which makes the decision. This is what makes every recovery action explainable and audited.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend + pipeline + API | Python, FastAPI, Uvicorn |
| ORM + DB | SQLModel + SQLite (file-based, zero setup) |
| Dashboard | Streamlit (read-only, talks to FastAPI over REST) |
| Payments | Payment gateway test mode — Orders, Payments, Payment Links, Webhooks |
| LLM / AI | Indic-language LLM — classification fallback + Hinglish message drafting |
| Tunneling | ngrok (receives gateway webhooks locally) |
| Data generation | `faker` (Python) |

**Why an Indic-language LLM?** Hindi, Hinglish, and code-mixed Indic text need native fluency. Recovery messages need to feel natural to an Indian customer — not like a translated template. An LLM trained on Indic data does this natively; generic Western LLMs don't.

**Why two processes (FastAPI + Streamlit)?** Streamlit reruns its script on every interaction and can't run a persistent webhook server. FastAPI owns the pipeline. Streamlit is a thin dashboard on top. You can develop and test the pipeline entirely via `curl` without touching the UI.

---

## Setup

### Prerequisites

- Python 3.13+ (or whatever `uv` gives you)
- Payment gateway test-mode API keys
- Indic-language LLM API key
- ngrok (for webhook tunneling)

### Install

```bash
# clone and enter
git clone <repo-url> && cd aipunarartha

# create venv with uv (downloads Python automatically)
uv venv --python 3.13
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux

# install deps
uv pip install -r backend\requirements.txt
```

### Configure

```bash
cp backend\.env.example backend\.env
# fill in your payment gateway + LLM API keys
```

### Run

```bash
# generate 55 synthetic payment events
cd backend
python -m app.scripts.generate_synthetic_batch

# smoke test your API keys
python -m app.scripts.smoke_test

# run the full pipeline (classify -> decide -> execute)
python -m app.scripts.run_pipeline

# simulate recovery outcomes
python -m app.scripts.simulate_outcomes

# start the API server
uvicorn app.main:app --reload --port 8000
```

In a second terminal:
```bash
cd dashboard
streamlit run app.py
```

Or just run `run_demo.bat` to start both.

---

## Recovery Outcomes

Recovery outcomes are **simulated** using bucket-conditioned probabilities based on industry data:

| Bucket | Assumed recovery rate | Basis |
|---|---|---|
| insufficient_funds | 60% | Industry: retries succeed after 24h when salary credits hit |
| bank_timeout | 70% | Bank outages are transient, retry within 2h usually works |
| 3ds_failed | 30% | Some customers retry and complete auth on second attempt |
| card_expired | 5% | Card needs update — almost never self-resolves |
| generic_decline | 15% | Vague declines, some resolve on retry |
| ambiguous | 10% | Unknown root cause, low confidence |

These are **not** measured production results. We state the assumption honestly. A real deployment would replace these with actual outcome data.

---

## Differentiation

| Tool | Limitation |
|---|---|
| Chargebee Revive / Retain | Locked to Chargebee's billing platform |
| Stripe Smart Retries | Black-box, no audit trail, no Indic-language support |
| Churn Buster / ChurnKey | US-centric SaaS, not built for Indian payment failure patterns |
| Credgenics | Enterprise-grade, expensive, overkill for SME recovery |
| **AIPunarartha** | Narrow, transparent, native to the payment gateway, every decision audited, Hinglish messaging via Indic-language LLM |

---

## What's Next

- **Real SMS/WhatsApp delivery** — replace simulated sends with actual Twilio/WhatsApp Business API
- **LLM voice synthesis** — generate actual Hinglish voice notes for recovery calls
- **A/B test retry timing** — measure real recovery rates per bucket and time-of-day, feed back into `action_rules.json`
- **Promise-to-pay tracker** — lightweight B2B receivables flow for overdue invoices
