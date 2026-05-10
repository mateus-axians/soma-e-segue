"""
conversation.py
Rules-based conversation state machine.

Each user (identified by phone number) has an in-memory state dict.
State survives as long as the server process is running.
On a cold restart, any mid-conversation state is lost and the user
just needs to start a new message — they'll be back at step 1.

Flow overview:
  idle
    → choose_type  (Expense / Income / Savings Transfer)

  [Expense]
    → exp_category → exp_amount → exp_description → exp_account → exp_person → exp_confirm

  [Income]
    → inc_type → inc_amount → inc_description → inc_account → inc_person → inc_confirm

  [Savings Transfer]
    → sav_amount → sav_description → sav_account → sav_person → sav_confirm
"""

import logging
from datetime import datetime

import sheets

logger = logging.getLogger(__name__)

# ─── State store ──────────────────────────────────────────────────────────────
# phone_number (str) → state dict
_states: dict[str, dict] = {}

def _get(phone: str) -> dict:
    return _states.get(phone, {"step": "idle", "data": {}})

def _set(phone: str, step: str, data: dict):
    _states[phone] = {"step": step, "data": data}

def _clear(phone: str):
    _states.pop(phone, None)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _numbered_menu(items: list[str], title: str, emoji: str = "  ") -> str:
    """Render a numbered menu. Returns empty string if no items."""
    if not items:
        return f"{title}\n\n(No items found — check the ⚙️ Setup sheet)"
    lines = [title, ""]
    for i, item in enumerate(items, 1):
        lines.append(f"{i}️⃣  {item}")
    lines.append("\n↩️  Type 0 to cancel")
    return "\n".join(lines)

def _pick(text: str, items: list[str]) -> str | None:
    """
    Accept a 1-based number or a matching name.
    Returns the matched item string, or None if invalid.
    """
    text = text.strip()
    # Try numeric pick
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(items):
            return items[idx]
        return None
    # Try case-insensitive name match
    lower = text.lower()
    for item in items:
        if item.lower().startswith(lower) or lower in item.lower():
            return item
    return None

def _parse_amount(text: str) -> float | None:
    """Parse a positive number from user input."""
    try:
        val = float(text.strip().replace(",", ".").replace("€", "").strip())
        return val if val > 0 else None
    except ValueError:
        return None

def _confirm_summary(data: dict) -> str:
    tx_type   = data.get("type", "")
    category  = data.get("category", "")
    amount    = data.get("amount", 0.0)
    desc      = data.get("description", "") or "(no description)"
    account   = data.get("account", "")
    person    = data.get("person", "")
    today     = datetime.now().strftime("%d/%m/%Y")

    icon = {"Expense": "💸", "Income": "💰", "Savings Transfer": "🏦"}.get(tx_type, "📋")

    return (
        f"{icon} *Confirm transaction:*\n\n"
        f"  Type:    {tx_type}\n"
        f"  Cat:     {category}\n"
        f"  Amount:  €{amount:.2f}\n"
        f"  Note:    {desc}\n"
        f"  Account: {account}\n"
        f"  Person:  {person}\n"
        f"  Date:    {today}\n\n"
        f"Reply *1* to confirm ✅\n"
        f"Reply *0* to cancel ❌"
    )


# ─── Main entry point ─────────────────────────────────────────────────────────

def handle_message(phone: str, text: str) -> str:
    """
    Process an incoming message from `phone` with body `text`.
    Returns the reply string to send back.
    """
    text = text.strip()
    state = _get(phone)
    step  = state["step"]
    data  = state["data"].copy()

    # ── Global cancel ──────────────────────────────────────────────────────
    if text in ("0", "cancel", "Cancel", "CANCEL", "stop", "Stop"):
        _clear(phone)
        return "❌ Cancelled. Send any message to start a new transaction."

    # ── Global help ────────────────────────────────────────────────────────
    if text.lower() in ("help", "?", "menu"):
        _clear(phone)
        return _step_idle()

    # ── Route by current step ──────────────────────────────────────────────
    if step == "idle":
        return _step_idle(phone)

    elif step == "choose_type":
        return _handle_choose_type(phone, text, data)

    elif step == "exp_category":
        return _handle_exp_category(phone, text, data)
    elif step == "exp_amount":
        return _handle_amount(phone, text, data, next_step="exp_description")
    elif step == "exp_description":
        return _handle_description(phone, text, data, next_step="exp_account")
    elif step == "exp_account":
        return _handle_account(phone, text, data, next_step="exp_person")
    elif step == "exp_person":
        return _handle_person(phone, text, data, next_step="exp_confirm")
    elif step == "exp_confirm":
        return _handle_confirm(phone, text, data)

    elif step == "inc_type":
        return _handle_inc_type(phone, text, data)
    elif step == "inc_amount":
        return _handle_amount(phone, text, data, next_step="inc_description")
    elif step == "inc_description":
        return _handle_description(phone, text, data, next_step="inc_account")
    elif step == "inc_account":
        return _handle_account(phone, text, data, next_step="inc_person")
    elif step == "inc_person":
        return _handle_person(phone, text, data, next_step="inc_confirm")
    elif step == "inc_confirm":
        return _handle_confirm(phone, text, data)

    elif step == "sav_amount":
        return _handle_amount(phone, text, data, next_step="sav_description")
    elif step == "sav_description":
        return _handle_description(phone, text, data, next_step="sav_account")
    elif step == "sav_account":
        return _handle_account(phone, text, data, next_step="sav_person")
    elif step == "sav_person":
        return _handle_person(phone, text, data, next_step="sav_confirm")
    elif step == "sav_confirm":
        return _handle_confirm(phone, text, data)

    else:
        _clear(phone)
        return _step_idle(phone)


# ─── Step handlers ────────────────────────────────────────────────────────────

def _step_idle(phone: str = None) -> str:
    if phone:
        _set(phone, "choose_type", {})
    return (
        "👋 *Welcome to the Finance Tracker!*\n\n"
        "What would you like to log?\n\n"
        "1️⃣  Expense\n"
        "2️⃣  Income\n"
        "3️⃣  Savings Transfer\n\n"
        "↩️  Type 0 at any time to cancel"
    )

def _handle_choose_type(phone, text, data):
    mapping = {"1": "Expense", "2": "Income", "3": "Savings Transfer",
               "expense": "Expense", "income": "Income", "transfer": "Savings Transfer",
               "savings transfer": "Savings Transfer"}
    tx_type = mapping.get(text.lower())
    if not tx_type:
        return "Please reply 1, 2 or 3:\n\n1️⃣ Expense\n2️⃣ Income\n3️⃣ Savings Transfer"

    data["type"] = tx_type

    cfg = sheets.get_config()

    if tx_type == "Expense":
        cats = cfg.get("categories", [])
        _set(phone, "exp_category", data)
        return _numbered_menu(cats, "📂 *Which category?*")

    elif tx_type == "Income":
        types = cfg.get("income_types", [])
        _set(phone, "inc_type", data)
        return _numbered_menu(types, "📈 *Which type of income?*")

    else:  # Savings Transfer
        _set(phone, "sav_amount", data)
        return "🏦 *How much are you transferring?*\n\n(Just the number, e.g. 200 or 150.50)\n\n↩️ Type 0 to cancel"

# ── Expense path ──────────────────────────────────────────────────────────────

def _handle_exp_category(phone, text, data):
    cfg = sheets.get_config()
    cats = cfg.get("categories", [])
    chosen = _pick(text, cats)
    if not chosen:
        return _numbered_menu(cats, "❓ Please pick a valid category number:") 
    data["category"] = chosen
    _set(phone, "exp_amount", data)
    return f"✅ _{chosen}_\n\n💶 *How much?*\n(e.g. 45.50)\n\n↩️ Type 0 to cancel"

# ── Income path ───────────────────────────────────────────────────────────────

def _handle_inc_type(phone, text, data):
    cfg = sheets.get_config()
    types = cfg.get("income_types", [])
    chosen = _pick(text, types)
    if not chosen:
        return _numbered_menu(types, "❓ Please pick a valid income type:")
    data["category"] = chosen   # reuse same field
    _set(phone, "inc_amount", data)
    return f"✅ _{chosen}_\n\n💶 *How much?*\n(e.g. 1500)\n\n↩️ Type 0 to cancel"

# ── Shared steps (amount, description, account, person, confirm) ──────────────

def _handle_amount(phone, text, data, next_step):
    amount = _parse_amount(text)
    if amount is None:
        return "❓ Please enter a positive number (e.g. 45.50 or 200)"
    data["amount"] = amount
    _set(phone, next_step, data)
    return "📝 *Short description?*\n\nE.g. 'Mercadona shop', 'November salary'\nOr type *skip* to leave blank\n\n↩️ Type 0 to cancel"

def _handle_description(phone, text, data, next_step):
    data["description"] = "" if text.lower() in ("skip", "0", "-", "none") else text
    cfg = sheets.get_config()
    accounts = cfg.get("accounts", [])
    _set(phone, next_step, data)
    return _numbered_menu(accounts, "🏦 *Which account?*")

def _handle_account(phone, text, data, next_step):
    cfg = sheets.get_config()
    accounts = cfg.get("accounts", [])
    chosen = _pick(text, accounts)
    if not chosen:
        return _numbered_menu(accounts, "❓ Please pick a valid account:")
    data["account"] = chosen
    cfg = sheets.get_config()
    members = cfg.get("members", [])
    _set(phone, next_step, data)
    label = "Who paid?" if data.get("type") == "Expense" else "Who received it?"
    return _numbered_menu(members, f"👤 *{label}*")

def _handle_person(phone, text, data, next_step):
    cfg = sheets.get_config()
    members = cfg.get("members", [])
    chosen = _pick(text, members)
    if not chosen:
        return _numbered_menu(members, "❓ Please pick a valid person:")
    data["person"] = chosen
    _set(phone, next_step, data)
    return _confirm_summary(data)

def _handle_confirm(phone, text, data):
    if text.strip() != "1":
        _clear(phone)
        return "❌ Cancelled. Send any message to start again."

    # Write to Google Sheets
    tx_type     = data["type"]
    category    = data.get("category", "")
    amount      = data.get("amount", 0.0)
    description = data.get("description", "")
    account     = data.get("account", "")
    person      = data.get("person", "")
    today       = datetime.now()

    ok = sheets.log_transaction(
        date=today,
        description=description,
        tx_type=tx_type,
        category=category,
        amount=amount,
        account=account,
        person=person,
        notes="via WhatsApp bot",
    )

    _clear(phone)

    if ok:
        icon = {"Expense": "💸", "Income": "💰", "Savings Transfer": "🏦"}.get(tx_type, "✅")
        return (
            f"{icon} *Logged!*\n\n"
            f"  {category}  —  €{amount:.2f}\n"
            f"  {account}  ·  {person}\n\n"
            "Send any message to log another."
        )
    else:
        return (
            "⚠️ Transaction could not be saved to the sheet.\n"
            "Please check the server logs and try again."
        )