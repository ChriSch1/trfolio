# 📊 TRFolio - Dein Portfolio, automatisch analysiert

**TRFolio** macht aus deinen PDF-Invoices von Trade Republic automatisch eine **intelligente Portfolio-Analyse** – mit Kursdaten, Gewinn/Verlust-Tracking, interaktiven Dashboards und dokumentierter Ablage.

**Wenige Klicks. Alle deine Investitionen übersichtlich visualisiert und dokumentiert.**

---
## Ziel und Motivation

TRFolio ist ein privates Softwareprojekt, welches aus dem Ziel entstanden ist, Abrechnungen zu Zinsen, Dividenden und Orders zentral und übersichtlich zu dokumentieren. Darüber hinaus bietet es die Möglichkeit Auswertungen und Analysefunktionen, die über die grundlegenden Möglichkeiten der Trade-Republic-App hinausgehen umzusetzen.

## 🚀 Quick Start (2 Minuten)

### 1. Python & uv installieren
```bash
# Python 3.12+ erforderlich
python --version  # Mindestens 3.12

# uv installieren (falls noch nicht vorhanden)
```

### 2. Repository clonen & Setup
```bash
git clone https://github.com/ChriSch1/trfolio.git
cd trfolio

# Abhängigkeiten automatisch installieren & virtuelle Umgebung erstellen
uv sync
```

`uv sync` liest `pyproject.toml` und installiert alle Abhängigkeiten automatisch in eine lokale `.venv`-Umgebung – kein manuelles `pip install` nötig.

### 3. Konfiguration
```bash
cp src/config_sample.py src/config.py
```

Öffne `src/config.py` und passe die Pfade an (siehe [Konfiguration im Detail](#-konfiguration-im-detail)).

### 4. PDFs vorbereiten & Modus wählen

Je nachdem, ob du TRFolio **zum ersten Mal nutzt** oder **bestehende Daten erweiterst**, gibt es zwei Modi:

#### **Modus A: Initialisierung (Neues Portfolio)**
```python
# In src/config.py:
enable_initialization_portfolio = True
```

**Das bedeutet:**
- 📁 Deine PDFs liegen im **Verarbeitungs-Verzeichnis** (`data_dir`)
- 🆕 Die Datenbank wird **von Grund auf neu** erstellt
- 🔄 Alle PDFs in `data_dir` werden **gescannt und verarbeitet**
- 💾 Eine neue `portfolio.duckdb` in `portfolio_dir` wird geschrieben

**Anwendungsfall:** Du hast bereits alle Trade Republic Invoices gesammelt, manuell oder per älterem Lauf umbenannt, und möchtest die komplette Portfolio-Historie einlesen.

```bash
# PDFs liegen bereits hier (gesammelt):
./Trade Republic/invoices/
  ├─ buy_AAPL_2023-01-15.pdf
  ├─ dividend_MSFT_2023-06-10.pdf
  └─ ...

# Dann: Initialisierung = True
uv run python main.py
# ✓ Liest alle PDFs aus data_dir, erstellt neue Datenbank
```

#### **Modus B: Update (Portfolio erweitern)**
```python
# In src/config.py:
enable_initialization_portfolio = False
```

**Das bedeutet:**
- 📥 Neue Roh-PDFs liegen im **Invoice-Verzeichnis** (`invoice_dir`) – so wie Trade Republic sie benennt (z.B. `Abrechnung.pdf`, `Abrechnung (1).pdf`)
- 📤 PDFs werden **aus `invoice_dir` eingelesen**, Daten extrahiert, Dateien **umbenannt** und anschließend in **`data_dir` verschoben**
- 🔗 Bestehende Datenbank in `portfolio_dir` wird **erweitert** (nicht überschrieben)
- 🚀 Nur neue Transaktionen werden hinzugefügt (Duplikatschutz aktiv)

**Anwendungsfall:** Du nutzt TRFolio schon länger und lädst regelmäßig neue Invoices von Trade Republic hoch.

```bash
# Neue Roh-PDFs (so wie von Trade Republic heruntergeladen):
./Trade Republic/
  ├─ Abrechnung.pdf
  ├─ Abrechnung (1).pdf
  └─ ...

# Nach der Verarbeitung:
./Trade Republic/invoices/      ← verarbeitete, umbenannte PDFs
./Trade Republic/portfolio/     ← portfolio.duckdb + portfolio.csv

# Dann: Initialisierung = False
uv run python main.py
# ✓ Liest Roh-PDFs aus invoice_dir, extrahiert Daten
# ✓ Benennt Dateien um und verschiebt sie in data_dir
# ✓ Erweitert bestehende Datenbank
```

### 5. Daten extrahieren
```bash
uv run python main.py
```

Die Anwendung:
- ✅ Liest alle PDFs aus dem konfigurierten Verzeichnis ein
- ✅ Extrahiert Transaktionsdaten
- ✅ Benennt die PDFs aussagekräftig um und verschiebt sie (Modus B)
- ✅ Speichert alles in einer lokalen DuckDB-Datenbank
- ✅ Exportiert ein CSV-Backup

### 6. Dashboard starten
```bash
uv run streamlit run app.py
```

Das Dashboard öffnet sich automatisch im Browser.

---

## 🧪 App mit Sample-Portfolio testen

Du möchtest TRFolio ausprobieren, hast aber noch keine eigenen Trade Republic PDFs? Das Repository enthält eine fertige **Sample-Datenbank** mit fiktiven Transaktionsdaten, mit der du alle Features sofort erkunden kannst – ganz ohne `main.py` ausführen zu müssen.

### Sample-Datenbank einrichten

```bash
# 1. Konfiguration anlegen (falls noch nicht geschehen)
cp src/config_sample.py src/config.py

# 2. Zielverzeichnis für die Datenbank anlegen
mkdir -p "Trade Republic/portfolio"

# 3. Sample-Datenbank ins richtige Verzeichnis kopieren
cp sample/sample_portfolio.duckdb "Trade Republic/portfolio/portfolio.duckdb"

# 4. Dashboard direkt starten (kein main.py notwendig)
uv run streamlit run app.py
```

Das Sample-Portfolio enthält fiktive Transaktionen mit:
- 📈 Aktien-Käufe und -Verkäufe
- 📌 ETF-Sparpläne
- 💰 Dividenden und Zinserträge
- 🪙 Krypto-Transaktionen

Damit kannst du alle Dashboard-Tabs erkunden, bevor du deine eigenen Daten einliest.

---

## 📚 Detaillierte Funktionsweise

### Projektstruktur

```
trfolio_private_development/
├── main.py              # Extraktion: PDFs einlesen, verarbeiten, DB befüllen
├── app.py               # Dashboard: Streamlit-Anwendung starten
├── pyproject.toml       # Abhängigkeiten (wird von uv gelesen)
├── src/
│   ├── config_sample.py   # Vorlage für deine persönliche Konfiguration
│   ├── config.py          # Deine persönliche Konfiguration (nicht im Repo)
│   ├── config_reader.py   # Hilfsfunktion zum Laden der Konfiguration
│   ├── data_extractor.py  # PDF-Text extrahieren & Felder parsen
│   ├── file_handler.py    # Verzeichnisse lesen, Dateien umbenennen & verschieben
│   ├── storage.py         # DuckDB-Datenbankzugriff & Speicherung
│   ├── ticker_mapper.py   # ISIN → Ticker-Auflösung (OpenFIGI + yfinance)
│   ├── position_manager.py # FIFO-Positionsberechnung
│   ├── stock_split_handler.py # Kursanpassungen bei Aktiensplits
│   ├── name_cleaner.py    # Bereinigung von Firmennamen aus PDFs
│   ├── models.py          # Datenmodell (Pydantic)
│   ├── utils.py           # Hilfsfunktionen
│   └── dashboard/         # Streamlit-Seiten und -Komponenten
│       ├── data_loader.py
│       ├── calculations.py
│       ├── config_loader.py
│       ├── sidebar.py
│       ├── theme.py
│       └── components/
├── sample_portfolio/
│   └── sample_portfolio.duckdb  # Fertige Demo-Datenbank (fiktive Daten)
└── tests/               # Unit-Tests
```

### Verzeichnisse zur Laufzeit (außerhalb des Repos)

Diese Verzeichnisse werden **lokal auf deinem Rechner** angelegt und sind **nicht im Repository** (via `.gitignore` ausgeschlossen):

| Config-Variable | Standard-Pfad | Zweck |
|---|---|---|
| `invoice_dir` | `./Trade Republic/` | **Quell-Verzeichnis** für neue Roh-PDFs von Trade Republic. Hier liegen frisch heruntergeladene Abrechnungen wie `Abrechnung.pdf`, `Abrechnung (1).pdf` etc. |
| `data_dir` | `./Trade Republic/invoices/` | **Ziel-Verzeichnis** für verarbeitete PDFs. Hierhin werden Dateien nach der Extraktion umbenannt (z.B. `buy_AAPL_2025-01-15.pdf`) und verschoben. Im Initialisierungs-Modus werden PDFs von hier eingelesen. |
| `portfolio_dir` | `./Trade Republic/portfolio/` | **Daten-Verzeichnis**. Enthält die DuckDB-Datenbank (`portfolio.duckdb`) und den CSV-Export. |

**Wichtig:** `db_path` und `csv_path` liegen standardmäßig in `portfolio_dir` und müssen in den meisten Fällen nicht separat konfiguriert werden.

### Wie funktioniert TRFolio?

TRFolio folgt einem **3-Schritt-Prozess**:

#### **Schritt 1: Extraktion (main.py)**

**Modus B (regelmäßiges Update):**
```
invoice_dir  →  Roh-PDFs ("Abrechnung.pdf", "Abrechnung (1).pdf" ...)
  ↓ Text extrahieren
  ↓ Daten parsen (Datum, ISIN, Betrag, Typ …)
  ↓ Datei umbenennen (z.B. buy_AAPL_2025-01-15.pdf)
  ↓ Datei nach data_dir verschieben
  ↓ Datensatz in DuckDB (portfolio_dir) schreiben
```

**Modus A (Initialisierung):**
```
data_dir  →  bereits gesammelte & benannte PDFs
  ↓ Text extrahieren
  ↓ Daten parsen
  ↓ Datensatz in neue DuckDB (portfolio_dir) schreiben
```

**Was wird extrahiert?**
- 📅 Transaktionsdatum
- 💰 Kaufpreis, Menge, Gesamtsumme
- 📌 ISIN (Wertpapier-Identifikation)
- 💵 Gebühren, Steuern, Nettobetrag
- 🪙 Währung & Wechselkurse

**Unterstützte Transaktionstypen:**
- 📈 Aktien & ETFs kaufen/verkaufen
- 📌 ETF-Sparpläne
- 💰 Dividenden & Zinserträge
- 🪙 Krypto-Transaktionen

#### **Schritt 2: Speicherung (DuckDB-Datenbank)**

TRFolio speichert alle Daten in einer **lokalen DuckDB-Datenbank** in `portfolio_dir` (kein Cloud-Upload, 100% privat):

```
📦 portfolio.duckdb  (lokal, in portfolio_dir)
 ├─ Alle Transaktionen
 ├─ Ticker-Cache (ISIN → Yahoo Finance Ticker)
 ├─ Berechnete FIFO-Positionen
 └─ Historische Kurse (via yfinance)
```

**Duplikat-Schutz**: Die gleiche Transaktion wird nicht zweimal eingefügt.

**CSV-Backup**: Automatisch wird auch eine `portfolio.csv` in `portfolio_dir` erstellt.

#### **Schritt 3: Dashboard (Streamlit App)**

Das interaktive Dashboard zeigt dir alles auf einen Blick:

| Tab | Was siehst du? |
|-----|---|
| **📈 Overview** | Dein komplettes Portfolio in einer Übersicht |
| **📊 Stocks Deep Dive** | Jede Aktie im Detail – Gewinn/Verlust, bester/schlechtester Trade |
| **🪙 Crypto Deep Dive** | Deine Kryptowährungen separat analysiert |
| **📌 ETF Deep Dive** | ETF-Sparpläne & deren Performance |
| **💰 Income** | Alle Dividenden- und Zinserträge, Steuern, monatliche Trends |
| **📜 Transaction Log** | Kompletter Transaktionsverlauf zum Filtern & Suchen |

**Automatisch berechnet:**
- 💹 Unrealisierte Gewinne/Verluste (FIFO)
- ✅ Realisierte Gewinne aus verkauften Positionen
- 📊 Branchen-Verteilung (Sektor-Analyse)
- 🌍 Multi-Währungs-Konvertierung (zu EUR)
- 📈 Performance-Trends (monatlich, jährlich)

---

### Was passiert hinter den Kulissen?

#### **PDF-Parsing**

TRFolio nutzt fortgeschrittene Text-Verarbeitung:
```
PDF-Text → Regex-Muster → Findet Preise, Daten, ISINs → Validierung
```

Beispiel: Aus diesem PDF-Text:
```
Kauf von 5 Anteilen Apple Inc.
Preis pro Anteil: €150,25
Gesamtbetrag: €751,25
ISIN: US0378331005
```

Extrahiert TRFolio automatisch:
```python
{
  "name": "Apple Inc.",
  "isin": "US0378331005",
  "unit_price": 150.25,
  "unit_amount": 5.0,
  "net_cashflow": -751.25
}
```

#### **Aktuelle Kurse abrufen**

TRFolio verbindet sich mit **Yahoo Finance**, um automatisch aktuelle Kurse zu laden:

```
ISIN (z.B. IE00B4L5Y983)
  ↓
Konvertierung zu Ticker (z.B. EUNL.DE) via OpenFIGI + isin_overrides
  ↓
Kurs abrufen (z.B. €110,50)
  ↓
Gewinn/Verlust berechnen
```

**Wichtig**: Das funktioniert ohne API-Keys. TRFolio nutzt die öffentliche Yahoo Finance API.

#### **Intelligente Caching-Strategie**

Um schnell zu sein, cacht TRFolio:
- 💾 **Transaktionsdaten**: 5 Minuten (`transaction_cache_ttl`)
- 💾 **Kursdaten**: 1 Stunde (`price_cache_ttl`)

So laden Daten schneller, ohne die API zu überlasten.

---

### 🔧 Konfiguration im Detail

Die Konfiguration liegt in `src/config.py` (wird von `src/config_sample.py` als Vorlage kopiert) und nutzt **Pydantic Settings**. Einstellungen können auch über Umgebungsvariablen mit dem Präfix `PORTFOLIO_` gesetzt werden (z.B. `PORTFOLIO_INVOICE_DIR`).

```python
# ───────────────────────────────────────────────────
# 📁 Verzeichnis-Konfiguration
# ───────────────────────────────────────────────────

# invoice_dir: Quell-Verzeichnis für neue Roh-PDFs von Trade Republic.
# Hier liegen frisch heruntergeladene Abrechnungen so wie Trade Republic
# sie benennt: "Abrechnung.pdf", "Abrechnung (1).pdf", "Abrechnung (2).pdf" ...
# Im Update-Modus (enable_initialization_portfolio = False) liest TRFolio
# diese Dateien ein, extrahiert die Daten, benennt sie um und
# verschiebt sie anschließend nach data_dir.
invoice_dir: Path = Path("./Trade Republic")

# data_dir: Ziel-Verzeichnis für verarbeitete PDFs.
# Hier landen alle Invoices nach der Extraktion mit einem sprechenden
# Dateinamen, z.B. "buy_AAPL_2025-01-15.pdf" oder "dividend_MSFT_2025-06-01.pdf".
# Im Initialisierungs-Modus (enable_initialization_portfolio = True)
# werden PDFs direkt aus diesem Verzeichnis eingelesen – nützlich,
# wenn du bereits eine Sammlung umbenannter Dateien hast.
data_dir: Path = Path("./Trade Republic/invoices/")

# portfolio_dir: Daten-Verzeichnis für Datenbank und CSV-Export.
# Hier werden portfolio.duckdb und portfolio.csv abgelegt.
# Dieses Verzeichnis wird nicht mit PDFs befüllt.
portfolio_dir: Path = Path("./Trade Republic/portfolio/")

# Pfad zur lokalen DuckDB-Datenbank (liegt in portfolio_dir)
db_path: Path = Path("./Trade Republic/portfolio/portfolio.duckdb")

# ───────────────────────────────────────────────────
# 🔧 Feature-Flags
# ───────────────────────────────────────────────────
# True  = PDFs direkt aus data_dir einlesen (Ersteinrichtung / Bulk-Import)
# False = Roh-PDFs aus invoice_dir einlesen, umbenennen, verschieben (Normalbetrieb)
enable_initialization_portfolio: bool = False

enable_csv_export: bool = True          # CSV nach jedem Lauf exportieren
enable_price_fetching: bool = True      # Aktuelle Kurse via yfinance laden
enable_duplicate_detection: bool = True # Duplikate verhindern

# ───────────────────────────────────────────────────
# 🪙 Kryptowährungen
# ───────────────────────────────────────────────────
# Mapping von Trade Republic Bezeichnung zu Yahoo Finance Ticker
crypto_tokens = {
    "bitcoin": "BTC-USD",
    "ethereum": "ETH-USD",
    # weitere Kryptowährungen nach Bedarf ergänzen
}

# ───────────────────────────────────────────────────
# ⏱️ Cache-Einstellungen (in Sekunden)
# ───────────────────────────────────────────────────
price_cache_ttl: int = 3600       # Kursdaten: 1 Stunde
transaction_cache_ttl: int = 300  # Transaktionsdaten: 5 Minuten
```

---

TRFolio speichert alles **lokal auf deinem Computer** – keine Cloud, keine externen Dienste außer Yahoo Finance für Kursdaten.

### Welche Börsen werden unterstützt?

Alle Wertpapiere, die **Trade Republic unterstützt**:
- 🇩🇪 Xetra (z.B. AAPL.DE)
- 🇬🇧 London Stock Exchange (z.B. AAPL.L)
- 🇺🇸 NASDAQ/NYSE (z.B. AAPL)
- 🇨🇭 SIX Swiss (z.B. AAPL.SW)
- Und viele mehr...

### Beispiel Workflow

1. Event auf Trade Republic tritt ein (Kauf, Zinsen, Verkauf etc.)
2. Export der Abrechnung in ein persönliches Cloud - Verzeichnis (auto. Benennung "Abrechnung.pdf")
3. Dieses Verzeichnis ist das invoice_dir angeben
4. Ort auswählen, an dem die Abrechnungen archiviert und das Portfolio abgelegt werden sollen (HardDrive, Cloud, lokal) -> data_dir & portfolio_dir
5. main.py übernimmt die Archivierung, Benennung und Database-Erweiterung

### Offene ToDos

- Steuerverrechnungen (z.B. Anwendung Verlusttopf) können aktuell nicht verarbeitet werden.
