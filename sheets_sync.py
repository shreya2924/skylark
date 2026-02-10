"""Google Sheets 2-way sync: read pilots, drones, missions; write pilot status and drone status."""
import pandas as pd
from typing import Optional

import config

# Lazy client
_sheets_client = None

def _get_client():
    global _sheets_client
    if _sheets_client is None and config.use_google_sheets():
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
            creds = Credentials.from_service_account_file(str(config.CREDENTIALS_PATH), scopes=scopes)
            _sheets_client = gspread.authorize(creds)
        except Exception as e:
            raise RuntimeError(f"Google Sheets auth failed: {e}") from e
    return _sheets_client

def _sheet_to_df(client, sheet_id: str, worksheet_name: str = "Sheet1") -> pd.DataFrame:
    """Fetch first sheet as DataFrame. Assumes first row is header."""
    book = client.open_by_key(sheet_id)
    sheet = book.worksheet(worksheet_name)
    rows = sheet.get_all_values()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows[1:], columns=rows[0])

def _normalize_empty(val):
    if val is None or (isinstance(val, str) and val.strip() in ("", "–", "-", "—")):
        return "–"
    return str(val).strip()

def _df_to_sheet(client, sheet_id: str, df: pd.DataFrame, worksheet_name: str = "Sheet1"):
    """Write DataFrame to sheet. Replaces content; first row = header."""
    book = client.open_by_key(sheet_id)
    sheet = book.worksheet(worksheet_name)
    # Fill NaN and empty as "–" for consistency
    out = df.fillna("–").astype(str)
    out = out.applymap(lambda x: "–" if str(x).strip() in ("", "nan", "None") else x)
    rows = [out.columns.tolist()] + out.values.tolist()
    sheet.clear()
    if rows:
        sheet.update(rows, value_input_option="USER_ENTERED")

# --- Public API ---

def read_pilot_roster() -> pd.DataFrame:
    if config.use_google_sheets():
        try:
            client = _get_client()
            return _sheet_to_df(client, config.PILOT_SHEET_ID)
        except Exception as e:
            # Fallback to local CSV on any Sheets error
            pass
    path = config.DATA_DIR / "pilot_roster.csv"
    return pd.read_csv(path).fillna("–")

def read_drone_fleet() -> pd.DataFrame:
    if config.use_google_sheets():
        try:
            client = _get_client()
            return _sheet_to_df(client, config.DRONE_SHEET_ID)
        except Exception:
            pass
    path = config.DATA_DIR / "drone_fleet.csv"
    return pd.read_csv(path).fillna("–")

def read_missions() -> pd.DataFrame:
    if config.use_google_sheets():
        try:
            client = _get_client()
            return _sheet_to_df(client, config.MISSIONS_SHEET_ID)
        except Exception:
            pass
    path = config.DATA_DIR / "missions.csv"
    return pd.read_csv(path).fillna("–")

def write_pilot_roster(df: pd.DataFrame) -> None:
    """Write full pilot roster back to sheet (used after status/assignment updates)."""
    df = df.copy()
    for c in df.columns:
        df[c] = df[c].apply(lambda x: _normalize_empty(x))
    if config.use_google_sheets():
        try:
            client = _get_client()
            _df_to_sheet(client, config.PILOT_SHEET_ID, df)
            return
        except Exception as e:
            raise RuntimeError(f"Failed to sync pilot roster to Google Sheets: {e}") from e
    # Local: write to CSV
    path = config.DATA_DIR / "pilot_roster.csv"
    df.to_csv(path, index=False)

def write_drone_fleet(df: pd.DataFrame) -> None:
    """Write full drone fleet back to sheet (status updates)."""
    df = df.copy()
    for c in df.columns:
        df[c] = df[c].apply(lambda x: _normalize_empty(x))
    if config.use_google_sheets():
        try:
            client = _get_client()
            _df_to_sheet(client, config.DRONE_SHEET_ID, df)
            return
        except Exception as e:
            raise RuntimeError(f"Failed to sync drone fleet to Google Sheets: {e}") from e
    path = config.DATA_DIR / "drone_fleet.csv"
    df.to_csv(path, index=False)
