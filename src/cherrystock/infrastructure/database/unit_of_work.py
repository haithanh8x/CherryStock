from __future__ import annotations

from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from cherrystock.infrastructure.database.repositories import (
    IndexRepository,
    IndicatorRepository,
    RSEvaluationRepository,
    SmartMoneyRepository,
    TickerRepository,
    TrendRepository,
)


class DuckDBUnitOfWork:
    """Wrap one business write operation in a single DuckDB transaction."""

    def __init__(self, factory: DuckDBConnectionFactory) -> None:
        self._factory = factory
        self.connection = None
        self.indexes: IndexRepository | None = None
        self.indicators: IndicatorRepository | None = None
        self.rs_evaluations: RSEvaluationRepository | None = None
        self.smart_money: SmartMoneyRepository | None = None
        self.tickers: TickerRepository | None = None
        self.trends: TrendRepository | None = None

    def __enter__(self) -> "DuckDBUnitOfWork":
        self.connection = self._factory.create_writer()
        self.connection.execute("BEGIN")
        self.indexes = IndexRepository(self.connection)
        self.indicators = IndicatorRepository(self.connection)
        self.rs_evaluations = RSEvaluationRepository(self.connection)
        self.smart_money = SmartMoneyRepository(self.connection)
        self.tickers = TickerRepository(self.connection)
        self.trends = TrendRepository(self.connection)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            if exc_type is None:
                self.connection.execute("COMMIT")
            else:
                self.connection.execute("ROLLBACK")
        finally:
            self.connection.close()
            self.connection = None
            self.indexes = None
            self.indicators = None
            self.rs_evaluations = None
            self.smart_money = None
            self.tickers = None
            self.trends = None
