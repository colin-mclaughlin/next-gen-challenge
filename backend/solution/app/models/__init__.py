"""Database models: one class per table, with relationships between them.

Importing this package registers every model on `Base.metadata`, which is the complete schema.
"""
from app.models.base import Base
from app.models.client import Client
from app.models.exchange_rate import ExchangeRate
from app.models.holding import Holding
from app.models.performance import PerformanceSnapshot
from app.models.portfolio import Portfolio
from app.models.security import PricePoint, Security
from app.models.transaction import Transaction, TransactionType

__all__ = [
    "Base",
    "Client",
    "ExchangeRate",
    "Holding",
    "PerformanceSnapshot",
    "Portfolio",
    "PricePoint",
    "Security",
    "Transaction",
    "TransactionType",
]
