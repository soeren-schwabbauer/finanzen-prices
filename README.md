# finanzen-prices

Tägliche ETL-Pipeline für ETF-Schlusskurse (Xetra, EUR) auf Databricks. Kursdaten werden über die Alpha Vantage API abgerufen und per idempotentem `MERGE` in die Delta-Tabelle `workspace.finanzen_prices.etf_daily_closing_prices` in Unity Catalog geladen. Die Ausführung übernimmt ein geplanter Lakeflow-Job (`ETF_Daily_Update`, Mo–Fr 23:00 Europe/Vienna).

## Übersicht

* **Datenquelle:** Alpha Vantage, Funktion `TIME_SERIES_DAILY` (Xetra-Kurse in EUR)
* **Zieltabelle:** `workspace.finanzen_prices.etf_daily_closing_prices` (Delta, Key: `date` + `isin`)
* **Aktualisierung:** idempotenter `MERGE INTO` – erneutes Ausführen erzeugt keine Duplikate, ältere Bestandsdaten bleiben erhalten
* **Historie:** `outputsize: compact` liefert die letzten ~100 Handelssitzungen pro Instrument

## Verfolgte ETFs

| ISIN | Ticker | Name |
| --- | --- | --- |
| IE00BK5BQT80 | VWCE.DEX | Vanguard FTSE All-World UCITS ETF |
| IE00B5BMR087 | SXR8.DEX | iShares Core S&P 500 UCITS ETF |
| LU0908500753 | LYP6.DEX | Amundi STOXX Europe 600 UCITS ETF |

Das Instrument-Mapping (`isin`, `ticker`, `name`, `active`) wird zentral in `config/etfs.yaml` gepflegt.

## Repo-Struktur

```text
finanzen-prices/
├── config/
│   ├── etfs.yaml            # Datenquelle, Instruments, Zieltabelle, Secrets
│   └── jobs.yaml            # Job-Definitionen für setup_jobs
├── notebooks/
│   └── update_etf_prices    # ETL: Abruf, Validierung, MERGE, Kontroll-Query
└── setup/
    ├── setup_secrets        # Secret-Scope und API-Key anlegen
    └── setup_jobs           # Jobs aus config/jobs.yaml erstellen/aktualisieren
```

## Zieltabelle

| Spalte | Typ | Beschreibung |
| --- | --- | --- |
| `date` | DATE | Handelstag (NOT NULL, Teil des Merge-Keys) |
| `isin` | STRING | ISIN des ETF (NOT NULL, Teil des Merge-Keys) |
| `ticker` | STRING | Alpha-Vantage-Ticker (Xetra, `*.DEX`) |
| `name` | STRING | Bezeichnung des ETF |
| `close_eur` | DOUBLE | Schlusskurs in EUR (NOT NULL, muss > 0 sein) |

## Einrichtung

1. **Secret anlegen** (einmalig): Notebook [setup_secrets](setup/setup_secrets) ausführen. Es erstellt den Secret-Scope `finance` und speichert den Alpha-Vantage-API-Key unter `alpha-vantage`. Der Key wird interaktiv per `getpass` eingegeben und erscheint nicht im Notebook.
2. **ETL testen**: Notebook [update_etf_prices](notebooks/update_etf_prices) manuell ausführen. Es legt Schema und Tabelle bei Bedarf an (`CREATE SCHEMA/TABLE IF NOT EXISTS`), prüft die Daten (nicht leer, keine Duplikate, alle erwarteten ISINs vorhanden) und führt den `MERGE` aus.
3. **Job deployen**: Notebook [setup_jobs](setup/setup_jobs) ausführen. Es erzeugt den geplanten Job `ETF_Daily_Update` aus `config/jobs.yaml` (Quartz-Cron `0 0 23 ? * MON-FRI`, Zeitzone Europe/Vienna, keine Retries, Timeout 600 s). Die Notebook-Pfade werden vor der Änderung validiert; ein bereits existierender Job gleichen Namens wird aktualisiert, nicht dupliziert.

## Konfiguration

* **Instrument hinzufügen/entfernen:** Eintrag in `config/etfs.yaml` (`instruments`) ergänzen bzw. `active: false` setzen – Code muss nicht geändert werden.
* **Job-Zeitplan anpassen:** `config/jobs.yaml` editieren und `setup_jobs` erneut ausführen.
* **Zieltabelle/Quelle ändern:** `target`- bzw. `source`-Block in `config/etfs.yaml`.

## Hinweise

* Der Alpha-Vantage-Free-Tier begrenzt die Abfragen pro Minute – das ETL pausiert daher 1 Sekunde zwischen den Instrumenten.

