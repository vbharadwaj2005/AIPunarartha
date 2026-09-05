from core.config import get_settings
from ui.components import (
    badge, card_close, card_open, divider, hero, info_box, subnote,
)
from ui.nav import nav_cards

hero(
    "Failed-Payment Recovery Engine",
    "A small but complete system that watches failed payments, works out why each "
    "one failed, and decides a bounded recovery action for it — with every decision "
    "traceable back to the rule (or model output) that produced it.",
)

divider()

card_open(
    f"Dashboard navigation {badge('6 views', 'outline')}",
    "Pick a view from the sidebar; each one reads the same database.",
)
nav_cards()
card_close()

divider()

_settings = get_settings()
if not (_settings.razorpay_key_id or _settings.sarvam_api_key):
    info_box(
        "Keyless sandbox mode: <strong>Razorpay</strong> and <strong>Sarvam AI</strong> "
        "keys are not set in .env, so decisions and messages still run but no real payment "
        "link or model call is made. Add the keys any time to go live.",
        kind="info",
    )

subnote(
    "Recovered amounts reflect <strong>simulated outcomes</strong>, "
    "not live settlements. The simulation is described honestly in the README."
)