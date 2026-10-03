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
