import yfinance as yf
import pandas as pd
import os
import datetime as dt

# 💰 ISIN → Ticker Mapping
tickers = {
    "IE00BK5BQT80": "VWCE.DE",   # Vanguard FTSE All-World UCITS ETF
    "IE00B5BMR087": "CSPX.AS",  # iShares Core S&P 500 UCITS ETF
    "LU0908500753": "LYP6.DE"   # Lyxor MSCI EMU ETF
}

# 📂 Zielordner (wird automatisch angelegt, falls nicht existiert)
output_dir = "./data/depot"
os.makedirs(output_dir, exist_ok=True)

for isin, ticker in tickers.items():
    print(f"\n📊 Lade Daten für {ticker} ({isin})")

    # Pfad zur CSV-Datei
    path = f"{output_dir}/{isin}.csv"

    # 🔍 Prüfe, ob bereits eine Datei existiert
    if os.path.exists(path):
        # Alte Daten laden
        old = pd.read_csv(path)
        old["datum"] = pd.to_datetime(old["datum"])
        last_date = old["datum"].max().date()
        start_date = last_date + dt.timedelta(days=1)
        print(f"➡️  Lade neue Daten ab {start_date}")

        # Nur neue Daten abrufen
        data = yf.download(ticker, start=start_date, progress=False, auto_adjust=False)
    else:
        print("🆕 Keine bestehende Datei gefunden – lade alle Daten.")
        data = yf.download(ticker, period="max", progress=False)

    # Falls keine neuen Daten vorhanden sind, überspringen
    if data.empty:
        print("⚠️  Keine neuen Daten gefunden.")
        continue

    # Daten aufbereiten
    data = data.reset_index()
    data = data[["Date", "Close"]]
    data.columns = ["datum", "preis"]

    # Wenn alte Datei existiert → zusammenführen
    if os.path.exists(path):
        combined = pd.concat([old, data], ignore_index=True)
        combined = combined.drop_duplicates(subset=["datum"]).sort_values("datum")
        combined.to_csv(path, index=False)
        print(f"✅ Datei aktualisiert: {path}")
    else:
        # Neue Datei anlegen
        data.to_csv(path, index=False)
        print(f"✅ Neue Datei erstellt: {path}")

print("\n🏁 Fertig! Alle ETFs wurden aktualisiert.")

