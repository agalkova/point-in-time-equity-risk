from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MERGER_TYPES = {"cash_mergers", "stock_mergers", "stock_and_cash_mergers"}
WORTHLESS_TYPES = {"worthless_removals"}


@dataclass(frozen=True)
class OutcomePriceResolution:
    prices: pd.DataFrame
    audit: pd.DataFrame


def fill_internal_price_gaps(price: pd.DataFrame, *, maximum_gap_days: int = 3) -> pd.DataFrame:
    """Carry the prior close through short gaps only when later trading resumes."""
    if maximum_gap_days < 0:
        raise ValueError("maximum_gap_days must not be negative")
    if maximum_gap_days == 0:
        return price.copy()
    prior = price.ffill(limit=maximum_gap_days)
    resumes = price.bfill(limit=maximum_gap_days).notna()
    return price.where(price.notna(), prior.where(resumes))


def _number(row: pd.Series, name: str, default: float = 0.0) -> float:
    value = pd.to_numeric(pd.Series([row.get(name)]), errors="coerce").iloc[0]
    return float(value) if pd.notna(value) else float(default)


def resolve_outcome_prices(
    price: pd.DataFrame,
    corporate_actions: pd.DataFrame,
    *,
    successor_prices: pd.DataFrame | None = None,
    maximum_internal_gap_days: int = 3,
    action_match_calendar_days: int = 7,
) -> OutcomePriceResolution:
    """Create a valuation panel for outcomes without altering signal-date features.

    Short internal data gaps are marked at the prior close. A terminal cash, stock,
    or stock-and-cash merger is valued at its contractual consideration and then
    carried as cash or through the acquirer. Unknown terminal disappearances remain
    missing so they cannot silently become zero-return observations.
    """
    work = price.sort_index().astype(float)
    resolved = fill_internal_price_gaps(work, maximum_gap_days=maximum_internal_gap_days)
    successor = resolved if successor_prices is None else successor_prices.reindex(resolved.index)
    actions = corporate_actions.copy()
    if actions.empty:
        return OutcomePriceResolution(resolved, pd.DataFrame())
    actions["action_date"] = pd.to_datetime(actions["action_date"], errors="coerce").dt.normalize()
    actions["action_symbol"] = actions["action_symbol"].astype(str).str.upper()
    actions = actions[actions["action_type"].isin(MERGER_TYPES | WORTHLESS_TYPES)]

    rows: list[dict[str, object]] = []
    for action in actions.sort_values("action_date").itertuples(index=False):
        ticker = str(action.action_symbol).upper()
        if ticker not in resolved:
            continue
        action = pd.Series(action._asdict())
        action_date = pd.Timestamp(action["action_date"])
        observed_before = work.loc[work.index <= action_date, ticker].dropna()
        if observed_before.empty:
            continue
        last_date = observed_before.index.max()
        if abs((action_date - last_date).days) > int(action_match_calendar_days):
            continue

        # A ticker can later be reused by an unrelated security. Stop the old
        # security's synthetic consideration before a new observed run begins.
        future_observed = work.loc[work.index > action_date, ticker].dropna()
        reuse_dates = future_observed.index[
            future_observed.index > action_date + pd.Timedelta(days=30)
        ]
        resolution_end = reuse_dates.min() if len(reuse_dates) else None
        apply_dates = resolved.index[resolved.index >= action_date]
        if resolution_end is not None:
            apply_dates = apply_dates[apply_dates < resolution_end]
        if len(apply_dates) == 0:
            continue

        action_type = str(action["action_type"])
        status = "unresolved"
        acquirer = str(action.get("acquirer_symbol") or "").upper()
        if acquirer == "NAN":
            acquirer = ""
        if action_type == "cash_mergers":
            terminal_value = _number(action, "rate", np.nan)
            if np.isfinite(terminal_value) and terminal_value >= 0.0:
                resolved.loc[apply_dates, ticker] = terminal_value
                status = "cash_consideration"
        elif action_type in {"stock_mergers", "stock_and_cash_mergers"}:
            acquiree_rate = _number(action, "acquiree_rate", 1.0)
            acquirer_rate = _number(action, "acquirer_rate", np.nan)
            cash_rate = _number(action, "cash_rate", 0.0)
            if acquirer in successor and acquiree_rate > 0.0 and np.isfinite(acquirer_rate):
                successor_value = (
                    successor[acquirer].bfill(limit=maximum_internal_gap_days).loc[apply_dates]
                )
                consideration = successor_value.mul(acquirer_rate / acquiree_rate).add(cash_rate)
                resolved.loc[apply_dates, ticker] = consideration
                status = "successor_consideration"
        elif action_type in WORTHLESS_TYPES:
            resolved.loc[apply_dates, ticker] = 0.0
            status = "worthless_removal"

        if status != "unresolved":
            bridge_dates = resolved.index[
                (resolved.index > last_date) & (resolved.index < action_date)
            ]
            resolved.loc[bridge_dates, ticker] = float(observed_before.iloc[-1])

        rows.append(
            {
                "ticker": ticker,
                "last_observed_date": last_date,
                "action_date": action_date,
                "action_type": action_type,
                "acquirer_symbol": acquirer or None,
                "resolution_status": status,
            }
        )
    return OutcomePriceResolution(resolved, pd.DataFrame(rows))


def audit_episode_censoring(
    original_price: pd.DataFrame,
    resolved_price: pd.DataFrame,
    episodes: pd.DataFrame,
    *,
    horizon_days: int,
) -> pd.DataFrame:
    """Classify incomplete forward paths before and after outcome-price resolution."""
    index_positions = pd.Series(range(len(original_price.index)), index=original_price.index)
    rows: list[dict[str, object]] = []
    for row in episodes[["date", "ticker", "episode_id"]].itertuples(index=False):
        date = pd.Timestamp(row.date)
        if date not in index_positions or row.ticker not in original_price:
            continue
        position = int(index_positions.loc[date])
        mature = position + int(horizon_days) < len(original_price.index)
        if not mature:
            status = "recent_unmatured"
            original_missing = resolved_missing = np.nan
        else:
            future = original_price.iloc[position + 1 : position + 1 + horizon_days][row.ticker]
            repaired = resolved_price.iloc[position + 1 : position + 1 + horizon_days][row.ticker]
            original_missing = int(future.isna().sum())
            resolved_missing = int(repaired.isna().sum())
            if original_missing == 0:
                status = "complete"
            elif resolved_missing == 0:
                status = "resolved"
            elif future.notna().any() and future.last_valid_index() == future.index[-1]:
                status = "unresolved_internal_gap"
            else:
                status = "unresolved_terminal"
        rows.append(
            {
                "episode_id": row.episode_id,
                "date": date,
                "ticker": row.ticker,
                "horizon_days": int(horizon_days),
                "globally_mature": mature,
                "original_missing_days": original_missing,
                "resolved_missing_days": resolved_missing,
                "censoring_status": status,
            }
        )
    return pd.DataFrame(rows)
