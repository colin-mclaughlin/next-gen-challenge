from copy import deepcopy

import pytest

from app.services.crm_client import CrmError
from app.services.crm_mapper import map_crm_portfolio

META = {"retrieved_at": "2025-06-01T10:00:00Z", "source": "legacy-crm-v2"}


def account(**overrides):
    base = {
        "acct_ref": "P-9001",
        "acct_nickname": "Taxable Brokerage",
        "curr_val": {"amt": 482350.12, "ccy": "CAD"},
        "chg_1d": {"amt": 1520.44, "pct": 0.0032},
        "since_inception_pct": 0.187,
    }
    base.update(overrides)
    return base


def payload(accounts, meta=META):
    return {"client_record": {"client_id": "abc123", "full_name": "Jane Doe", "accounts": accounts}, "meta": meta}


def test_maps_documented_example_to_clean_schema():
    mapped = map_crm_portfolio(payload([account()]), "P-9001")
    assert mapped.model_dump(by_alias=True) == {
        "portfolioId": "P-9001",
        "clientId": "abc123",
        "label": "Taxable Brokerage",
        "currency": "CAD",
        "totalMarketValue": 482350.12,
        "dayChangeAmount": 1520.44,
        "dayChangePercent": 0.0032,
        "totalReturnSinceInception": 0.187,
        "asOf": "2025-06-01T10:00:00.000Z",
    }


def test_selects_account_by_acct_ref_not_position():
    accounts = [account(), account(acct_ref="P-9002", acct_nickname="Retirement Account")]
    mapped = map_crm_portfolio(payload(accounts), "P-9002")
    assert mapped.portfolio_id == "P-9002"
    assert mapped.label == "Retirement Account"


def test_finds_accounts_nested_under_relationships():
    nested = {"client_record": {"client_id": "abc123", "relationships": {"accounts": [account()]}}, "meta": {}}
    assert map_crm_portfolio(nested, "P-9001").total_market_value == 482350.12


def test_returns_none_when_account_not_in_payload():
    assert map_crm_portfolio(payload([account()]), "P-0000") is None


def test_missing_and_null_values_map_to_none_not_zero():
    sparse = account(curr_val={"amt": None, "ccy": "CAD"}, chg_1d=None, since_inception_pct="n/a")
    del sparse["acct_nickname"]
    mapped = map_crm_portfolio(payload([sparse], meta={}), "P-9001")
    assert mapped.label is None
    assert mapped.total_market_value is None
    assert mapped.day_change_amount is None
    assert mapped.day_change_percent is None
    assert mapped.total_return_since_inception is None
    assert mapped.as_of is None


def test_missing_currency_defaults_to_cad_and_case_is_normalised():
    assert map_crm_portfolio(payload([account(curr_val={"amt": 1})]), "P-9001").currency == "CAD"
    assert map_crm_portfolio(payload([account(curr_val={"amt": 1, "ccy": "usd"})]), "P-9001").currency == "USD"


def test_numeric_strings_are_accepted_but_booleans_are_not():
    assert map_crm_portfolio(payload([account(curr_val={"amt": "100.5"})]), "P-9001").total_market_value == 100.5
    assert map_crm_portfolio(payload([account(curr_val={"amt": True})]), "P-9001").total_market_value is None


def test_genuine_zero_stays_zero():
    mapped = map_crm_portfolio(payload([account(chg_1d={"amt": 0, "pct": 0})]), "P-9001")
    assert mapped.day_change_amount == 0
    assert mapped.day_change_percent == 0


def test_unparseable_retrieved_at_maps_to_none():
    assert map_crm_portfolio(payload([account()], meta={"retrieved_at": "yesterday"}), "P-9001").as_of is None


@pytest.mark.parametrize(
    "bad",
    [None, {}, {"client_record": "x"}, {"client_record": {"client_id": "abc123"}}, [1, 2]],
)
def test_structurally_unusable_payload_raises_bad_response(bad):
    with pytest.raises(CrmError) as info:
        map_crm_portfolio(bad, "P-9001")
    assert info.value.kind == "bad_response"


def test_missing_client_id_raises_bad_response():
    with pytest.raises(CrmError) as info:
        map_crm_portfolio({"client_record": {"accounts": [account()]}}, "P-9001")
    assert info.value.kind == "bad_response"


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf"), "NaN", "Infinity", "-Infinity", "1e999", True, False, "", "n/a"],
)
def test_invalid_numbers_become_null_in_every_numeric_field(value):
    mapped = map_crm_portfolio(payload([account(
        curr_val={"amt": value, "ccy": "CAD"},
        chg_1d={"amt": value, "pct": value},
        since_inception_pct=value,
    )]), "P-9001")

    for field in ("total_market_value", "day_change_amount", "day_change_percent", "total_return_since_inception"):
        assert getattr(mapped, field) is None, field


def test_numeric_strings_preserve_negative_changes_and_decimal_percentage_units():
    mapped = map_crm_portfolio(payload([account(
        curr_val={"amt": " 100.50 ", "ccy": "CAD"},
        chg_1d={"amt": "-1.25", "pct": "-0.0032"},
        since_inception_pct="-0.187",
    )]), "P-9001")

    assert mapped.total_market_value == 100.5
    assert mapped.day_change_amount == -1.25
    assert mapped.day_change_percent == -0.0032
    assert mapped.total_return_since_inception == -0.187


def test_zero_value_portfolio_preserves_all_numeric_zeroes():
    mapped = map_crm_portfolio(payload([account(
        curr_val={"amt": 0, "ccy": "CAD"},
        chg_1d={"amt": 0, "pct": 0}, since_inception_pct=0,
    )]), "P-9001")

    assert mapped.total_market_value == 0
    assert mapped.day_change_amount == 0
    assert mapped.day_change_percent == 0
    assert mapped.total_return_since_inception == 0


@pytest.mark.parametrize("container", [None, [], "unexpected", {}])
def test_missing_or_malformed_optional_containers_do_not_crash(container):
    mapped = map_crm_portfolio(payload([account(
        curr_val=container, chg_1d=container,
    )], meta=container), "P-9001")

    assert mapped.currency == "CAD"
    assert mapped.total_market_value is None
    assert mapped.day_change_amount is None
    assert mapped.day_change_percent is None
    assert mapped.as_of is None


def test_empty_accounts_list_means_no_matching_portfolio():
    assert map_crm_portfolio(payload([]), "P-9001") is None


def test_ignores_malformed_account_entries_when_selecting_requested_account():
    rows = [None, "invalid", {}, account(acct_ref="P-9002"), account()]
    mapped = map_crm_portfolio(payload(rows), "P-9001")
    assert mapped.portfolio_id == "P-9001"


@pytest.mark.parametrize("client_id", [None, "", "   ", 123, False])
def test_invalid_client_identifier_is_a_structural_error(client_id):
    raw = payload([account()])
    raw["client_record"]["client_id"] = client_id
    with pytest.raises(CrmError) as caught:
        map_crm_portfolio(raw, "P-9001")
    assert caught.value.kind == "bad_response"


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        ("2025-06-01T06:00:00-04:00", "2025-06-01T10:00:00.000Z"),
        ("2025-01-01T00:30:00+02:00", "2024-12-31T22:30:00.000Z"),
        ("2025-06-01T10:00:00", "2025-06-01T10:00:00.000Z"),
        (None, None),
    ],
)
def test_retrieved_at_normalizes_offsets_and_naive_utc_policy(timestamp, expected):
    mapped = map_crm_portfolio(payload([account()], meta={"retrieved_at": timestamp}), "P-9001")
    assert mapped.as_of == expected


def test_mapping_does_not_mutate_crm_payload():
    raw = payload([account(curr_val={"amt": "100.5", "ccy": "usd"})])
    original = deepcopy(raw)
    map_crm_portfolio(raw, "P-9001")
    assert raw == original
