"""Draw the headline figures for the S&P 500 test and the S&P 400 transfer.

Reads the prediction and annual tables written by run_modern_replication.py and
run_sp400_replication.py (reports/tables/, not committed), writes the small
summary tables behind each figure to docs/figures/data/, and saves the figures
as SVG in docs/figures/ (a wide and a narrow version, drawn at the pixel width they are shown at).

    python scripts/make_figures.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import figure_style as fs
from figure_style import plt

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"
OUT = ROOT / "docs" / "figures"

UNIVERSES = {
    "S&P 500": {
        "predictions": "modern_model_predictions.csv.gz",
        "annual": "modern_model_annual.csv",
        "color": fs.BLUE,
        "marker": "o",
    },
    "S&P 400": {
        "predictions": "v08_sp400_predictions.csv.gz",
        "annual": "v08_sp400_annual.csv",
        "color": fs.ORANGE,
        "marker": "s",
    },
}


def build_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Decile event rates, overall event rate and annual rank IC for each universe."""
    sys.path.insert(0, str(ROOT / "src"))
    from risk_managed_momentum.evaluation.ranking import decile_table

    deciles, annual = [], []
    for universe, spec in UNIVERSES.items():
        predictions = pd.read_csv(TABLES / spec["predictions"])
        table = decile_table(predictions, "risk_score")
        deciles.append(
            pd.DataFrame(
                {
                    "universe": universe,
                    "risk_decile": table["risk_decile"],
                    "event_rate": table["event_rate"],
                    "observations": table["observations"],
                    "overall_event_rate": predictions["target"].mean(),
                }
            )
        )
        yearly = pd.read_csv(TABLES / spec["annual"])
        annual.append(
            pd.DataFrame(
                {
                    "universe": universe,
                    "year": yearly["year"],
                    "mean_daily_rank_ic": yearly["mean_daily_rank_ic"],
                }
            )
        )
    deciles_frame, annual_frame = pd.concat(deciles), pd.concat(annual)
    data = OUT / "data"
    data.mkdir(parents=True, exist_ok=True)
    deciles_frame.to_csv(data / "decile_event_rates.csv", index=False)
    annual_frame.to_csv(data / "annual_rank_ic.csv", index=False)
    return deciles_frame, annual_frame


def decile_figure(deciles: pd.DataFrame, narrow: bool, out: Path = OUT) -> None:
    fig = fs.new_figure(4.6, 5.6)
    axis = fig.add_axes(
        [0.14 if narrow else 0.075, 0.13, 0.7 if narrow else 0.76, 0.6 if narrow else 0.62]
    )
    size = plt.rcParams["font.size"]
    for universe, spec in UNIVERSES.items():
        part = deciles[deciles["universe"] == universe].sort_values("risk_decile")
        rates = part["event_rate"].to_numpy() * 100
        average = float(part["overall_event_rate"].iloc[0]) * 100
        axis.axhline(average, color=spec["color"], lw=0.9, ls=(0, (4, 3)), alpha=0.7, zorder=1)
        axis.plot(
            part["risk_decile"],
            rates,
            color=spec["color"],
            lw=1.8,
            marker=spec["marker"],
            ms=5,
            mec="white",
            mew=0.8,
            label=universe,
            zorder=3,
        )
        axis.text(
            10.75, rates[-1], f"{rates[-1]:.1f}%", va="center", fontsize=size - 0.5, color=fs.INK
        )
        if not narrow:
            axis.annotate(
                f"{rates[0]:.1f}%",
                (1, rates[0]),
                xytext=(0, -14) if universe == "S&P 500" else (0, 12),
                textcoords="offset points",
                ha="center",
                va="center",
                fontsize=size - 0.5,
                color=fs.INK,
            )
        if not narrow:
            axis.text(
                10.75,
                average,
                f"average {average:.1f}%",
                va="center",
                fontsize=size - 1.5,
                color=fs.MUTED,
            )
    axis.set_xlim(0.5, 10.6)
    axis.set_xticks(range(1, 11))
    axis.tick_params(axis="x", length=0)
    axis.set_ylim(0, 35)
    axis.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    axis.set_xlabel(
        "Predicted-risk decile (1 = lowest, 10 = highest)" if not narrow else "Risk decile"
    )
    axis.legend(loc="upper left", bbox_to_anchor=(0, 1.02))
    fs.header(
        fig,
        1,
        "Drawdown rate by predicted-risk decile" if not narrow else "Drawdown rate by risk decile",
        "Share of stocks that fell 15%+ within 40 trading days, Jan 2020 - Aug 2026"
        if not narrow
        else "Fell 15%+ within 40 days · dashed: average",
        narrow,
    )
    fs.source(fig, "docs/figures/data/decile_event_rates.csv", narrow)
    name = "decile-event-rates" + fs.suffix()
    fs.save(
        fig,
        out / f"{name}.svg",
        "Drawdown rate by predicted-risk decile",
        "In both the S&P 500 and the S&P 400, the share of stocks that fell 15% or more within 40 trading days "
        "rises from the lowest to the highest predicted-risk decile. Dashed lines mark each index's overall rate.",
    )


def annual_figure(
    annual: pd.DataFrame, narrow: bool, out: Path = OUT, last_date: str = "Aug 4"
) -> None:
    fig = fs.new_figure(4.0, 4.8)
    axis = fig.add_axes(
        [
            0.15 if narrow else 0.075,
            0.14 if narrow else 0.13,
            0.81 if narrow else 0.9,
            0.6 if narrow else 0.62,
        ]
    )
    years = sorted(annual["year"].unique())
    bar = 0.36
    for k, (universe, spec) in enumerate(UNIVERSES.items()):
        part = (
            annual[annual["universe"] == universe]
            .set_index("year")
            .loc[years, "mean_daily_rank_ic"]
        )
        xs = np.arange(len(years)) + (k - 0.5) * (bar + 0.03)
        axis.bar(xs, part.to_numpy(), width=bar, color=spec["color"], label=universe, zorder=2)
    axis.axhline(0, color=fs.SPINE, lw=0.8)
    axis.set_xticks(
        range(len(years)),
        [str(y) if y != years[-1] else f"{y}*" for y in years]
        if not narrow
        else [f"'{str(y)[2:]}" + ("*" if y == years[-1] else "") for y in years],
    )
    axis.tick_params(axis="x", length=0)
    axis.set_ylim(0, 0.32)
    axis.set_ylabel("Mean daily rank IC")
    axis.legend(loc="lower left", ncol=2, bbox_to_anchor=(-0.01, 0.99))
    fs.header(
        fig,
        2,
        "Ranking quality by year",
        None
        if narrow
        else f"Mean daily Spearman correlation between risk score and forward loss · *2026 through {last_date}",
        narrow,
    )
    fs.source(fig, "docs/figures/data/annual_rank_ic.csv", narrow)
    name = "annual-rank-ic" + fs.suffix()
    fs.save(
        fig,
        out / f"{name}.svg",
        "Mean daily rank IC by year",
        "The risk ranking's mean daily rank IC is above zero in every test year from 2020 to 2026 in both "
        "indexes, ranging from about 0.09 to 0.30.",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--plain",
        type=Path,
        metavar="DIR",
        help="write versions without the figure label, title and source line to DIR",
    )
    args = parser.parse_args()
    out = OUT
    if args.plain:
        fs.PLAIN = True
        out = args.plain
    deciles, annual = build_tables()
    variants = ("wide", "mid", "narrow") if args.plain else ("wide", "narrow")
    for variant in variants:
        fs.VARIANT = variant
        narrow = variant != "wide"
        decile_figure(deciles, narrow, out)
        annual_figure(annual, narrow, out)


if __name__ == "__main__":
    main()
