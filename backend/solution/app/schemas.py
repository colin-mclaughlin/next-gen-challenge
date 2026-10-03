"""Public response models. Python attributes are snake_case; JSON is camelCase via aliases."""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PortfolioMetadata(ApiModel):
    """Task 1 output schema. Nullable fields are null when the CRM omits them (never a made-up 0)."""

    portfolio_id: str
    client_id: str
    label: str | None
    currency: str
    total_market_value: float | None
    day_change_amount: float | None
    day_change_percent: float | None
    total_return_since_inception: float | None
    as_of: str | None


class Holding(ApiModel):
    """Task 2 output item. Money rounded to 2 dp, ratios (decimals) to 6 dp."""

    ticker: str
    name: str
    asset_class: str
    quantity: float
    cost_basis_per_share: float
    price: float
    previous_close_price: float
    market_value: float
    weight_percent: float
    unrealized_gain_loss: float
    day_change_amount: float
    day_change_percent: float | None  # null when previous close is 0


class PerformancePoint(ApiModel):
    """Task 3 output item."""

    date: str  # ISO 8601 YYYY-MM-DD
    market_value: float
