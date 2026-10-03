# Task 1 unit tests

Run from `backend/solution/` with the virtual environment active:

```sh
python -m pytest tests/unit -v
```

These tests need no running CRM or listening network port. They exercise the
public mapper, an HTTP client with `httpx.MockTransport`, and the metadata
service with an injected asynchronous CRM stub. They preserve Task 1's current
float-based response contract; they do not introduce currency conversion,
authentication, caching, or a Decimal migration.

The existing tests already cover the documented schema, selecting a non-first
account, alternative nesting, unknown accounts, missing fields, numeric strings,
currency defaults, malformed payloads, upstream status codes, invalid JSON,
connection failures, and a CRM that stalls before sending headers.

## Added mapper tests (`unit/test_crm_mapper.py`)

| Test | What it verifies and why |
| --- | --- |
| `test_invalid_numbers_become_null_in_every_numeric_field` | Numeric/string NaN and infinity, overflowed numeric strings, booleans, empty strings, and invalid text become null across all four numeric fields. Non-finite values cannot safely enter ordinary JSON responses; booleans must not become money. |
| `test_numeric_strings_preserve_negative_changes_and_decimal_percentage_units` | Legacy numeric strings are parsed, losses retain their signs, and percentages are not multiplied by 100. Task 1 maps upstream values rather than formatting them for display. |
| `test_zero_value_portfolio_preserves_all_numeric_zeroes` | A genuinely empty-value account keeps zero for value, changes, and return. This distinguishes known zero from unavailable data. |
| `test_missing_or_malformed_optional_containers_do_not_crash` | Null, list, string, or empty-object money/change/meta containers use the documented null/CAD defaults. An awkward optional upstream field must not crash mapping. |
| `test_empty_accounts_list_means_no_matching_portfolio` | A valid empty account list yields no match, allowing the service to return 404 rather than treating it as a broken CRM schema. |
| `test_ignores_malformed_account_entries_when_selecting_requested_account` | Invalid sibling entries and another account do not prevent selecting the requested account. CRM results include multiple accounts. |
| `test_invalid_client_identifier_is_a_structural_error` | Null, blank, numeric, and boolean client IDs raise `bad_response`. A response without a usable required client identity is not valid metadata. |
| `test_retrieved_at_normalizes_offsets_and_naive_utc_policy` | Offset timestamps, including a year boundary, normalize to UTC; timezone-less timestamps follow the current UTC assumption; null remains null. This prevents shifted freshness timestamps. |
| `test_mapping_does_not_mutate_crm_payload` | Mapping leaves the original payload unchanged, including numeric strings and currency casing. Raw upstream data remains safe to reuse. |

## Added client tests (`unit/test_crm_client.py`)

| Test | What it verifies and why |
| --- | --- |
| `test_requests_json_using_get` | The CRM request uses GET and explicitly accepts JSON. This checks the integration's request contract. |
| `test_http_408_is_classified_as_timeout` | An upstream request-timeout response follows the same timeout path as 504. |
| `test_httpx_timeout_exceptions_are_classified_as_timeout` | Connect, read, write, and pool timeouts all become `CrmError("timeout")`, allowing consistent API failure handling. |
| `test_total_timeout_covers_response_body_and_cancels_the_read` | A CRM that sends headers and partial JSON but then stalls is interrupted by the total deadline. The pending read is cancelled rather than continuing after the caller fails. |
| `test_same_client_can_recover_after_network_failure` | The same client succeeds after a connection failure, proving an outage does not permanently break subsequent calls. |

The two deadline tests use a short configured timeout and a generous one-second
upper bound against a five-second stall; they do not assert exact timing.

## New service tests (`unit/test_portfolio_metadata_service.py`)

| Test | What it verifies and why |
| --- | --- |
| `test_fetches_requested_portfolio_from_crm_and_returns_mapped_metadata` | The service awaits the CRM with the exact requested ID and returns the clean nine-field result. Task 1 must obtain metadata from the external CRM. |
| `test_translates_crm_failures_into_public_errors` | Not-found, timeout, unavailable, and bad-response failures become the documented 404/504/502 status, code, and safe message. Internal upstream diagnostics are not exposed. |
| `test_successful_crm_response_without_requested_account_is_not_found` | A successful CRM HTTP response containing only other accounts still becomes a portfolio 404. Transport success does not imply the requested account exists. |
| `test_unusable_crm_payload_is_bad_gateway_instead_of_internal_error` | Null payload, absent record, and missing client identity are translated from mapper errors to `502 bad_crm_response`. Upstream schema failures must not become unhandled application errors. |
| `test_successful_request_after_failure_returns_fresh_crm_metadata` | The same service fetches and returns metadata after an outage. A failed request does not leave it in a permanently failed state. |

Run the full suite with `python -m pytest`. Existing `tests/http/` cases start the
real Node mock and verify actual endpoint responses. Unit tests do not replace
those integration checks.
