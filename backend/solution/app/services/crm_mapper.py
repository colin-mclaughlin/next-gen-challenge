"""Pure mapping from the legacy CRM payload to our PortfolioMetadata schema (Task 1)."""
import math
from datetime import datetime, timezone
from typing import Any

from app.schemas import PortfolioMetadata
from app.services.crm_client import CrmError

# Platform base currency per REQUIREMENTS.md; used only when the CRM omits `curr_val.ccy`.
DEFAULT_CURRENCY = "CAD"


def map_crm_portfolio(payload: Any, portfolio_id: str) -> PortfolioMetadata | None:
    """Select the requested account from a CRM payload and map it.

    - The CRM returns every account for the client; we match on `acct_ref`, never by position.
    - Accounts may live at `client_record.accounts` or `client_record.relationships.accounts`.
    - Missing/null/non-numeric values become None (never a made-up 0).

    Returns None when the payload has no account with this id.
    Raises CrmError(kind="bad_response") when the payload is structurally unusable.
    """
    record = payload.get("client_record") if isinstance(payload, dict) else None
    if not isinstance(record, dict):
        raise CrmError("bad_response", "CRM response is missing client_record.")

    accounts = _find_accounts(record)
    if accounts is None:
        raise CrmError("bad_response", "CRM response has no accounts list.")

    account = next((a for a in accounts if isinstance(a, dict) and _text(a.get("acct_ref")) == portfolio_id), None)
    if account is None:
        return None

    client_id = _text(record.get("client_id"))
    if client_id is None:
        raise CrmError("bad_response", "CRM response is missing client_record.client_id.")

    curr_val = _dict(account.get("curr_val"))
    chg_1d = _dict(account.get("chg_1d"))
    currency = _text(curr_val.get("ccy"))

    return PortfolioMetadata(
        portfolio_id=portfolio_id,
        client_id=client_id,
        label=_text(account.get("acct_nickname")),
        currency=currency.upper() if currency else DEFAULT_CURRENCY,
        total_market_value=_number(curr_val.get("amt")),
        day_change_amount=_number(chg_1d.get("amt")),
        day_change_percent=_number(chg_1d.get("pct")),
        total_return_since_inception=_number(account.get("since_inception_pct")),
        as_of=_iso_datetime(_dict(payload.get("meta")).get("retrieved_at")),
    )


def _find_accounts(record: dict) -> list | None:
    if isinstance(record.get("accounts"), list):
        return record["accounts"]
    relationships = _dict(record.get("relationships"))
    if isinstance(relationships.get("accounts"), list):
        return relationships["accounts"]
    return None


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str | None:
    """Non-empty trimmed string, or None."""
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _number(value: Any) -> float | None:
    """Finite number (numeric strings accepted, as legacy systems often stringify amounts), or None."""
    if isinstance(value, bool):  # bool is an int subclass; True is not an amount
        return None
    if isinstance(value, (int, float)):
        return value if math.isfinite(value) else None
    if isinstance(value, str) and value.strip():
        try:
            parsed = float(value)
        except ValueError:
            return None
        return parsed if math.isfinite(parsed) else None
    return None


def _iso_datetime(value: Any) -> str | None:
    """Normalised ISO 8601 UTC datetime (e.g. 2025-06-01T10:00:00.000Z), or None if absent/unparseable."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
