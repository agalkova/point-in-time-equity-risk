from __future__ import annotations

import io
import zipfile

import pandas as pd
import requests

FACTOR_URLS = {
    "five_factor": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"
    ),
    "momentum": (
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "F-F_Momentum_Factor_daily_CSV.zip"
    ),
}


def _parse_french_zip(content: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError("Expected exactly one CSV inside factor archive")
        lines = archive.read(names[0]).decode("utf-8", errors="replace").splitlines()
    header_index = next(
        index for index, line in enumerate(lines) if line.startswith(",") and ",RF" in line or line.startswith(",Mom")
    )
    frame = pd.read_csv(io.StringIO("\n".join(lines[header_index:])))
    date_column = frame.columns[0]
    date_text = frame[date_column].astype(str).str.strip()
    frame = frame[date_text.str.fullmatch(r"\d{8}")].copy()
    frame["date"] = pd.to_datetime(frame[date_column].astype(str).str.strip(), format="%Y%m%d")
    frame = frame.drop(columns=[date_column]).set_index("date")
    frame.columns = [str(column).strip().replace("Mkt-RF", "MKT_RF").upper() for column in frame]
    return frame.apply(pd.to_numeric, errors="coerce").div(100.0)


def download_french_factors(timeout_seconds: float = 30.0) -> pd.DataFrame:
    frames = []
    for url in FACTOR_URLS.values():
        response = requests.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        frames.append(_parse_french_zip(response.content))
    return frames[0].join(frames[1], how="inner").reset_index()


def load_french_factors(path: str) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["date"])
    frame["date"] = frame["date"].dt.normalize()
    return frame
