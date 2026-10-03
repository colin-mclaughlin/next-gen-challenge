-- GENERATED from app/models by `python -m app.db.schema_dump`. Do not edit by hand:
-- change the models, then regenerate. tests/unit/test_models.py fails if this file is stale.

CREATE TABLE clients (
	client_id VARCHAR(64) NOT NULL, 
	name VARCHAR NOT NULL, 
	CONSTRAINT pk_clients PRIMARY KEY (client_id)
);

CREATE TABLE exchange_rates (
	base_currency VARCHAR(3) NOT NULL, 
	quote_currency VARCHAR(3) NOT NULL, 
	rate DOUBLE NOT NULL, 
	CONSTRAINT pk_exchange_rates PRIMARY KEY (base_currency, quote_currency), 
	CONSTRAINT ck_exchange_rates_rate_positive CHECK (rate > 0)
);

CREATE TABLE securities (
	ticker VARCHAR(16) NOT NULL, 
	name VARCHAR NOT NULL, 
	asset_class VARCHAR NOT NULL, 
	sector VARCHAR, 
	dividend_yield DOUBLE, 
	fifty_two_week_low DOUBLE, 
	fifty_two_week_high DOUBLE, 
	price DOUBLE NOT NULL, 
	previous_close_price DOUBLE NOT NULL, 
	CONSTRAINT pk_securities PRIMARY KEY (ticker), 
	CONSTRAINT ck_securities_dividend_yield_non_negative CHECK (dividend_yield IS NULL OR dividend_yield >= 0), 
	CONSTRAINT ck_securities_price_non_negative CHECK (price >= 0), 
	CONSTRAINT ck_securities_previous_close_non_negative CHECK (previous_close_price >= 0)
);

CREATE TABLE portfolios (
	portfolio_id VARCHAR(64) NOT NULL, 
	client_id VARCHAR(64) NOT NULL, 
	label VARCHAR NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	CONSTRAINT pk_portfolios PRIMARY KEY (portfolio_id), 
	CONSTRAINT ck_portfolios_currency_iso_code CHECK (length(currency) = 3), 
	CONSTRAINT fk_portfolios_client_id_clients FOREIGN KEY(client_id) REFERENCES clients (client_id)
);

CREATE INDEX ix_portfolios_client_id ON portfolios (client_id);

CREATE TABLE security_price_history (
	ticker VARCHAR(16) NOT NULL, 
	date DATE NOT NULL, 
	price DOUBLE NOT NULL, 
	CONSTRAINT pk_security_price_history PRIMARY KEY (ticker, date), 
	CONSTRAINT ck_security_price_history_price_non_negative CHECK (price >= 0), 
	CONSTRAINT fk_security_price_history_ticker_securities FOREIGN KEY(ticker) REFERENCES securities (ticker)
);

CREATE TABLE holdings (
	holding_id VARCHAR(64) NOT NULL, 
	portfolio_id VARCHAR(64) NOT NULL, 
	ticker VARCHAR(16) NOT NULL, 
	quantity DOUBLE NOT NULL, 
	cost_basis_per_share DOUBLE NOT NULL, 
	CONSTRAINT pk_holdings PRIMARY KEY (holding_id), 
	CONSTRAINT uq_holdings_portfolio_id_ticker UNIQUE (portfolio_id, ticker), 
	CONSTRAINT ck_holdings_quantity_non_negative CHECK (quantity >= 0), 
	CONSTRAINT ck_holdings_cost_basis_non_negative CHECK (cost_basis_per_share >= 0), 
	CONSTRAINT fk_holdings_portfolio_id_portfolios FOREIGN KEY(portfolio_id) REFERENCES portfolios (portfolio_id), 
	CONSTRAINT fk_holdings_ticker_securities FOREIGN KEY(ticker) REFERENCES securities (ticker)
);

CREATE TABLE performance_snapshots (
	portfolio_id VARCHAR(64) NOT NULL, 
	date DATE NOT NULL, 
	market_value DOUBLE NOT NULL, 
	CONSTRAINT pk_performance_snapshots PRIMARY KEY (portfolio_id, date), 
	CONSTRAINT ck_performance_snapshots_market_value_non_negative CHECK (market_value >= 0), 
	CONSTRAINT fk_performance_snapshots_portfolio_id_portfolios FOREIGN KEY(portfolio_id) REFERENCES portfolios (portfolio_id)
);

CREATE TABLE transactions (
	transaction_id VARCHAR(64) NOT NULL, 
	holding_id VARCHAR(64) NOT NULL, 
	type VARCHAR(4) NOT NULL, 
	quantity DOUBLE NOT NULL, 
	price DOUBLE NOT NULL, 
	date DATE NOT NULL, 
	CONSTRAINT pk_transactions PRIMARY KEY (transaction_id), 
	CONSTRAINT ck_transactions_quantity_positive CHECK (quantity > 0), 
	CONSTRAINT ck_transactions_price_non_negative CHECK (price >= 0), 
	CONSTRAINT fk_transactions_holding_id_holdings FOREIGN KEY(holding_id) REFERENCES holdings (holding_id), 
	CONSTRAINT ck_transactions_transaction_type CHECK (type IN ('BUY', 'SELL'))
);

CREATE INDEX ix_transactions_holding_id_date ON transactions (holding_id, date);
