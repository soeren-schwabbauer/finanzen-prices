import yfinance as yf
import pandas as pd

# Beispiel: Vanguard FTSE All-World UCITS ETF (IE00BK5BQT80) -> Ticker "VWCE.DE"
tickers = {
    "IE00BK5BQT80": "VWCE.DE",   # Vanguard FTSE All-World UCITS ETF
    "IE00B5BMR087": "CSPX.AS",   # iShares Core S&P 500 UCITS ETF
    "LU0908500753": "LYSE.DE"    # Amundi Core Stoxx Europe 600 UCITS ETF
}

for isin, ticker in tickers.items():
    print(f"\n📊 Lade Daten für {ticker} ({isin})")
    data = yf.download(ticker, period="max")   # oder period="max"
    data = data.reset_index()
    data = data[["Date", "Close"]]
    data.columns = ["datum", "preis"]

    print(data.tail(5))  # letzte 5 Zeilen anzeigen
    data.to_csv(f"./data/depot/{isin}.csv", index=False)

