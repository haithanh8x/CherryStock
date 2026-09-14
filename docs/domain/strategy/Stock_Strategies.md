# Stock Strategy Reference — Top-Down Buy Evaluation

## Purpose

Domain reference for evaluating whether a stock is a suitable buy candidate using a six-step top-down framework. This document stores strategy knowledge, not Agent routing or executable procedure.

Evaluation order:

```text
Market
  → Market Breadth
  → Lagging / Stock Trend
  → Leading / Entry Timing
  → Volatility / Risk
  → Sentiment
  → Final Decision
```

Core principle: do not evaluate an individual stock in isolation. General market conditions and participation are checked before stock-level timing and risk.

## 1. Market condition

Classify the broad market as `UPTREND`, `SIDEWAY` or `DOWNTREND` using evidence such as:

- VN-Index / VN30 / relevant sector index;
- MA20 / MA50 / MA200 structure and slope;
- higher-high / higher-low or lower-high / lower-low structure;
- total market volume and up/down-day behavior;
- sector participation.

Typical healthy conditions include index above MA50, MA20 above MA50 with rising slopes, constructive price structure and supportive volume.

A downtrend materially reduces willingness to initiate aggressive long positions even when an individual ticker has a short-term signal.

## 2. Market breadth

Breadth checks whether index strength is broad or driven by a small number of large caps.

Useful evidence:

- advancing vs declining stocks;
- Advance/Decline ratio;
- percentage of stocks above MA20 / MA50 / MA200;
- new highs vs new lows;
- up volume vs down volume;
- number of participating sectors.

Indicative interpretation:

- **Strong breadth:** advancers dominate, percentage above short/medium MAs improves, new highs/up-volume expand and multiple sectors participate.
- **Neutral breadth:** mixed participation; selective buying rather than broad exposure.
- **Weak breadth:** decliners dominate, participation deteriorates, index gains are concentrated in a few names.

Thresholds such as `% above MA20 > 55%` or `< 40%` may be used as heuristics only when the data definition/universe is stable and the strategy explicitly adopts them.

## 3. Lagging indicators — stock trend confirmation

Trend evidence may include:

- price vs MA20 / MA50 / MA200;
- MA stacking and slope;
- higher-high / higher-low structure;
- MACD;
- ADX;
- Ichimoku;
- breakout behavior;
- volume confirmation.

A strong stock trend normally combines price above key moving averages, rising medium-term averages, constructive structure and supportive volume. Weak/declining structure generally blocks new long entries until the trend improves.

## 4. Leading indicators — entry timing

Timing evidence may include:

- RSI;
- Stochastic;
- CCI;
- MFI;
- Williams %R;
- bullish/bearish divergence;
- pullback to support/MA;
- breakout zone and volume.

Potentially favorable timing examples:

- confirmed broader/stock uptrend;
- controlled pullback toward support or MA20 and renewed strength;
- RSI/MFI behavior consistent with improving momentum rather than extreme chase;
- breakout with meaningful volume confirmation;
- no material bearish divergence.

Risky timing examples:

- severely overbought momentum combined with extended price distance from MA20/MA50;
- weakening money flow while price makes new highs;
- bearish divergence;
- breakout without volume confirmation.

Leading indicators should not be used as standalone automatic buy/sell triggers.

## 5. Volatility, stop-loss and position size

Risk evidence may include:

- ATR;
- Bollinger Band Width;
- historical volatility;
- recent daily range;
- gap behavior;
- distance from planned entry to invalidation/stop.

Position sizing reference:

```text
Risk Amount = Total Capital × Risk Per Trade
Position Size = Risk Amount / (Entry Price - Stop-loss Price)
```

Example:

```text
Total Capital = 100,000,000
Risk Per Trade = 1%
Risk Amount = 1,000,000
Entry Price = 50
Stop-loss Price = 47
Risk Per Share = 3
Position Size ≈ 333 shares
```

Higher volatility or wider invalidation distance normally implies smaller position size. Extreme volatility/news-driven movement may justify avoiding the trade.

## 6. Market sentiment

Sentiment evidence may include:

- news/social sentiment;
- foreign net buying/selling;
- margin usage;
- fund flow;
- retail behavior;
- sector hype/FOMO;
- panic-selling signs.

Interpret sentiment together with price/breadth rather than as a standalone signal.

- **Healthy:** constructive but not euphoric; price/breadth confirm.
- **Extreme greed:** chasing, stretched momentum/margin/hype; reduce aggressiveness.
- **Extreme fear:** possible opportunity only after price/breadth confirmation; oversold alone is insufficient.

## Decision classes

### Strong Buy Candidate

Typical combination:
- broad market uptrend;
- strong breadth;
- confirmed stock trend;
- reasonable entry timing;
- acceptable volatility/risk;
- sentiment not excessively euphoric.

### Selective Buy Candidate

Typical combination:
- market sideway or early uptrend;
- neutral breadth;
- stock shows relative strength;
- timing/risk remain acceptable.

Usually implies smaller position size and stricter risk management.

### Watchlist Only

Used when market/stock structure is improving but confirmation or entry timing is incomplete.

### Avoid

Typical when broad market/breadth and stock trend are weak, entry is materially overheated, volatility is extreme, or signals conflict enough that capital preservation dominates.

## Optional score model

Each of the six dimensions may be scored `0–2`:

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Market | Downtrend | Sideway | Uptrend |
| Market Breadth | Weak | Neutral | Strong |
| Lagging / Trend | Weak | Forming | Confirmed uptrend |
| Leading / Entry | Bad | Acceptable | Good |
| Volatility | Extreme risk | Manageable | Normal |
| Sentiment | Extreme | Slightly risky | Healthy |

Maximum score: 12.

Reference interpretation:

```text
10–12  Strong Buy Candidate
7–9    Selective Buy Candidate
5–6    Watchlist Only
0–4    Avoid
```

The score is a decision aid, not proof of expected return. Thresholds should be evaluated against historical data before being treated as production strategy logic.

## Risk principles

- Check market context before stock-level entry signals.
- Do not buy aggressively in a confirmed broad downtrend.
- Oversold RSI alone is not a buy condition.
- Avoid chasing when momentum, money flow and price extension are all extreme.
- Do not ignore breadth.
- Define invalidation/stop before position sizing.
- Position size should reflect risk per trade and stop distance.
- Reduce size as volatility rises.
- Treat divergence as evidence/warning, not an automatic trade command.
- Preserve capital when major signals conflict.

## Implementation note

If this reference is converted into an automated CherryStock strategy, its exact data universe, formulas, thresholds, lookback rules, point-in-time semantics, scoring weights and acceptance/evaluation criteria must be captured in a requirement + architecture/ADR before production use.
