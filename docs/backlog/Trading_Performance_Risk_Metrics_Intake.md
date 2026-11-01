# Trading Performance & Risk Metrics — Backlog Intake

- **Intake date:** 2026-11-01
- **Source:** [The 10 Mathematical Concepts Every Trader Should Understand](https://medium.com/coding-nexus/the-10-mathematical-concepts-every-trader-should-understand-4cddb7fb0de9) (Algo Insights, 2026-10-10)
- **Classification:** Quant Research / Strategy Evaluation + Portfolio, Position & Risk Management
- **Intake status:** Research note; proposed scope only. Not a canonical REQ and not authorization to implement or trade.
- **Primary backlog homes:** QT-02 (Event-Driven Backtesting), QT-04 (Quant Research Validation & Alpha Audit), QT-05 (Portfolio, Position & Risk Management), QT-11 (Paper Trading & Shadow Portfolio); coordinate with REQ-0037 (R/S-based Averaging Down Strategy and Position Sizing).
- **Related:** QT-03 (Vietnam Market Execution & Transaction Cost Simulator), QT-14 (Robust Portfolio Optimization & Tail-Risk Models).

## 1. Objective

Record a consistent, reusable metric framework for evaluating whether a trading strategy has positive net expectancy, survives adverse sequences and drawdowns, and sizes positions within explicit capital-risk limits.

These are **not technical chart indicators**. They are trade-level, strategy-level and portfolio-level evaluation / risk-control measures. Keep their ownership separate from the Indicator Engine and R/S source-effectiveness metrics.

## 2. Metric taxonomy and ownership

| Metric / concept | Correct classification | Definition / calculation intent | Primary owner |
|---|---|---|---|
| Risk/Reward Ratio (R:R) | Trade setup / payoff geometry | Planned loss per unit versus planned reward per unit, based on entry, stop and target. State convention explicitly (e.g. reward:risk = 3:1); article's example computes risk/reward = 1/3. | QT-08 strategy setup; QT-02 |
| Position Size | Portfolio / trade risk control | Quantity derived from risk budget divided by per-share risk, adjusted for lot size, liquidity, exposure and costs. | QT-05; REQ-0037 |
| Backtesting | Research methodology / validation process (not a metric) | Historical replay of entry, exit, orders, fills, cash and holdings under point-in-time rules. | QT-02 |
| Returns | Strategy performance | Cumulative and annualized return / CAGR; always report with benchmark, period, cash-flow convention and costs. | QT-02 / QT-04 |
| Drawdown | Portfolio downside risk | Peak-to-trough equity decline in currency and percentage; include maximum drawdown (MaxDD), duration and recovery time. | QT-05; QT-04 |
| Win Rate | Trade outcome statistic | Winning closed trades / all eligible closed trades; never interpret alone as strategy quality. | QT-02 / QT-04 |
| Average Win / Average Loss | Trade outcome distribution | Mean gain on winners and mean loss on losers, reported in currency and preferably R-multiples. | QT-02 / QT-04 |
| Expectancy | Strategy edge / per-trade expected value | Win probability × average win − loss probability × average loss; report gross and net of fees, taxes, spread, slippage and other applicable costs. | QT-04; QT-02 |
| Profit Factor | Strategy performance / payoff quality | Gross profit divided by absolute gross loss; report alongside expectancy and sample size. | QT-04 |
| Losing Streak Probability | Probabilistic risk analysis | Probability of k consecutive losses under an explicitly stated independent/constant win-probability assumption; supplement with empirical and dependence-aware simulation. | QT-04; QT-05 |
| Risk of Ruin | Capital survival / tail risk | Probability of breaching a defined capital or drawdown boundary over a specified horizon, conditional on the return distribution, sizing policy and assumptions. | QT-05; QT-14 |
| Stop Loss | Trade risk-control rule / exit policy (not a performance metric) | Predefined invalidation/exit level and planned loss; model gaps, price limits, non-fill and slippage so stop price is not treated as guaranteed execution. | QT-08; QT-02 / QT-03 |
| Profit Target | Trade exit policy (not a performance metric) | Predefined profit-taking level or exit rule; evaluate realized exits and partial fills, not just theoretical target distance. | QT-08; QT-02 / QT-03 |
| Return Volatility / Risk-adjusted Returns | Risk-adjusted strategy performance | Dispersion of periodic returns and risk-adjusted measures such as Sharpe / Sortino; use consistent frequency and risk-free assumptions. | QT-04; QT-05 |

## 3. Required evaluation bundle

A strategy/backtest report should not show a single headline metric in isolation. Minimum bundle:

1. **Trade distribution:** number of trades, win rate, average win, average loss, payoff ratio, expectancy, profit factor, median outcome and tail outcomes.
2. **Equity curve & drawdown:** cumulative return, CAGR, MaxDD, drawdown duration, recovery time and return volatility.
3. **Risk & survival:** planned risk per trade, realized risk, position sizing, exposure/concentration, losing-streak analysis and risk-of-ruin estimate under stated assumptions.
4. **Trade plan quality:** entry, stop, target, reward/risk, exit reason, realized R-multiple and stop/target execution quality.
5. **Robustness:** trade count and confidence intervals; TRAIN / VALIDATION / TEST separation; walk-forward and regime slices; sensitivity to parameters; benchmark comparison.
6. **Realism:** Vietnam-specific fees/tax, spread, slippage, price bands, tick/lot sizes, liquidity capacity, settlement, non-fill and delayed execution through QT-03.

## 4. Business rules / interpretation safeguards

- Win rate is not a standalone ranking criterion. A low-win-rate system can have positive expectancy; a high-win-rate system can lose money if average losses dominate.
- R:R is a planned payoff ratio, not realized profitability and not a substitute for win rate or expectancy.
- Stop loss does not guarantee the stated loss amount. Gaps, limit moves, liquidity and slippage can cause larger losses or non-fills.
- Position sizing must be computed from an explicit risk budget and stop distance, then constrained by portfolio exposure, liquidity and market-specific trading rules.
- Risk-of-ruin and losing-streak calculations must disclose assumptions. The simple formula p^k assumes independent trials with a stable loss probability; actual strategies may have correlated losses and regime dependence.
- Backtest metrics must be net of realistic costs and based on point-in-time, survivorship-aware data. Avoid look-ahead, leakage, overfitting and multiple-testing bias.
- Report sample size and uncertainty. A small number of trades is not sufficient evidence of durable edge.
- Never promote a strategy or enable live execution solely because one metric (including CAGR, win rate, Sharpe or profit factor) looks attractive.
- No automatic broker order placement, live deployment, or production score/weight change is authorized by this research intake.

## 5. Ownership and overlap boundaries

- **QT-02 — Backtesting Engine:** produce trade ledger, equity curve, returns, trade distribution, expectancy, profit factor and drawdown from reproducible event-driven simulation.
- **QT-03 — Execution Simulator:** provide realistic fills and transaction costs; stop/target outcomes and net performance depend on this contract.
- **QT-04 — Research Validation & Alpha Audit:** own statistical interpretation, OOS/walk-forward validation, uncertainty, regime robustness and strategy promotion evidence.
- **QT-05 — Portfolio / Position / Risk Engine:** own risk budget, position sizing, aggregate exposure, drawdown limits, losing-streak stress and risk-of-ruin / capital-survival controls.
- **QT-11 — Paper Trading:** monitor the same metrics on shadow/paper results and reconcile simulated versus observed execution; do not redefine metric formulas.
- **REQ-0037 — R/S Averaging Down:** apply shared QT-02/03/04/05 contracts to compare bounded multi-tranche sizing against a non-averaging baseline. Do not implement a second independent position-sizing or backtest framework.
- **QT-14 — Portfolio Optimization & Tail Risk:** extend beyond single-strategy ruin/drawdown to portfolio-level tail-risk and allocation analysis.

## 6. Suggested delivery sequence

1. BA intake: confirm scope and merge with existing QT-02 / QT-04 / QT-05 proposals; do not create a duplicate strategy-metrics project.
2. Architecture: define one canonical trade/equity/risk ledger and shared metric definitions, units, time horizons and cost conventions.
3. Implementation: calculate metrics from the shared ledger; persist reproducible run IDs, strategy/version, universe, data cutoff, cost model and assumptions.
4. Validation: independent reconciliation against hand-calculated fixtures; leakage-safe OOS/walk-forward and regime analysis; verify risk controls under adverse sequences.
5. Paper phase: compare simulated and shadow execution before any separate production approval.

## 7. Source note

The article introduces risk/reward, position sizing, backtesting, drawdown, returns, win rate, losing-streak probabilities, risk of ruin, stop losses and profit targets, and also discusses average win/loss, maximum drawdown, profit factor, volatility and expectancy. This intake preserves those concepts but separates **processes**, **trade rules**, **performance statistics** and **portfolio risk controls** so they are routed to the correct CherryStock domains.
