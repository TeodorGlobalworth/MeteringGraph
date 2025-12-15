# Building Metering System - Neo4j Graph Application

System do zarządzania strukturą licznikowania budynków z interaktywną wizualizacją grafową.

## Funkcje

- **Multi-project support**: Twórz wiele niezależnych projektów dla różnych budynków
- **Interaktywny graf**: Wizualizacja hierarchii liczników z możliwością ekspansji i nawigacji
- **Tree view**: Hierarchiczny widok drzewa z filtrowaniem i wyszukiwaniem
- **CRUD operacje**: Dodawanie, edycja i usuwanie węzłów (liczniki, rozdzielnie, odbiory)
- **Bulk import**: Import węzłów z pliku CSV
- **Export/Import**: Eksport i import całych projektów w formacie JSON
- **Readings management**: Rejestrowanie odczytów liczników z wizualizacją wykresów
- **Responsive design**: Obsługa desktop i mobile (tablets)

## Technologie

- **Backend**: Python 3.11, Flask
- **Databases**: Neo4j 5.x (graf), TimescaleDB (timeseries)
- **Frontend**: Bootstrap 5, Cytoscape.js, Chart.js
- **Deployment**: Docker, Docker Compose

## Wymagania

- Docker Desktop (Windows)
- Co najmniej 4GB RAM dla kontenerów
- Porty 5000, 5432, 7474, 7687 dostępne

## Instalacja i Uruchomienie

### 1. Uruchom Docker Compose

```powershell
cd C:\Users\tteter\Python\MeteringGraph
docker-compose up --build
```

Pierwsze uruchomienie potrwa kilka minut (pobieranie obrazów i budowanie).

### 2. Poczekaj na inicjalizację

Sprawdź logi:
```powershell
docker-compose logs -f
```

Poczekaj aż zobaczysz:
- Neo4j: `Started.` lub `Remote interface available at http://localhost:7474/`
- TimescaleDB: `database system is ready to accept connections`
- Flask: `Running on http://0.0.0.0:5000`

### 3. Otwórz aplikację

Główna aplikacja: **http://localhost:5000**

Dodatkowe interfejsy:
- Neo4j Browser: http://localhost:7474 (user: `neo4j`, password: `metering123`)
- TimescaleDB: `localhost:5432` (user: `metering_user`, password: `metering_pass123`)

## Użytkowanie

### Tworzenie Projektu

1. Na stronie głównej kliknij **"New Project"**
2. Podaj nazwę projektu
3. Wybierz typ zużycia (water/electricity/heating)
4. Kliknij **"Create Project"**

### Dodawanie Węzłów

**Sposób 1: Przez graf**
1. Otwórz projekt
2. Kliknij węzeł (np. główny licznik)
3. Prawym przyciskiem myszy → **"Add Child Node"**
4. Wypełnij formularz

**Sposób 2: Bulk import**
1. Pobierz template CSV: kliknij **"Bulk Import"** → **"Download Template"**
2. Plik zawiera pełną dokumentację wszystkich kolumn (linie zaczynające się od #)
3. Usuń komentarze (linie #) lub zostaw - parser je zignoruje
4. Wypełnij plik CSV swoimi danymi
5. Upload pliku przez modal "Bulk Import"

### Struktura CSV dla Bulk Import

**Kolumny wymagane:**

| Kolumna | Opis | Dozwolone wartości |
|---------|------|-------------------|
| `name` | Unikalna nazwa węzła | Dowolny tekst |
| `type` | Typ węzła | `Meter`, `Distribution`, `Consumer` |
| `subtype_or_category` | Podtyp lub kategoria | Zobacz tabele poniżej |

**Wartości subtype_or_category:**

| Typ węzła | Dozwolone wartości |
|-----------|-------------------|
| `Meter` | `Main`, `Submeter` |
| `Distribution` | `Main Panel`, `Sub Panel` |
| `Consumer` | `Lighting`, `HVAC`, `Elevator`, `Pumps`, `Ventilation`, `Outlets`, `Equipment`, `Other` |

**Kolumny opcjonalne:**

| Kolumna | Opis | Format/Wartości |
|---------|------|-----------------|
| `utility_type` | Typ medium | `electricity`, `water`, `heating`, `gas` |
| `parent_name` | Nazwa węzła nadrzędnego | Musi dokładnie pasować do istniejącego węzła |
| `description` | Opis węzła | Dowolny tekst |
| `serial_number` | Numer seryjny | Dowolny tekst |
| `location` | Lokalizacja | Dowolny tekst |
| `installation_date` | Data instalacji | Format: `YYYY-MM-DD` |

**Przykładowy plik CSV:**

```csv
name,type,subtype_or_category,utility_type,parent_name,description,serial_number,location,installation_date
Main Electricity Meter,Meter,Main,electricity,,Główny licznik elektryczny,EL-001,Parter,2024-01-15
Floor 1 Submeter,Meter,Submeter,electricity,Main Electricity Meter,Podlicznik piętra 1,EL-002,Piętro 1,2024-02-01
Distribution Panel F1,Distribution,Main Panel,electricity,Floor 1 Submeter,Rozdzielnia piętra 1,DP-001,Korytarz,2024-02-10
LED Lighting,Consumer,Lighting,electricity,Distribution Panel F1,Oświetlenie LED,,,2024-03-01
```

**Ważne zasady:**
- Węzły rodzicielskie (parent_name) muszą być zdefiniowane **PRZED** węzłami dziećmi
- Wielkość liter ma znaczenie w kolumnach `type` i `utility_type`
- Plik template zawiera komentarze z instrukcją (linie zaczynające się od #)
- Parser automatycznie ignoruje linie komentarzy

### Nawigacja w Grafie

- **Click węzeł**: Wybiera węzeł, pokazuje kontekst (przodkowie + dzieci)
- **Double-click węzeł**: Rozwija sąsiedztwo (dodaje więcej węzłów do grafu)
- **Prawy przycisk**: Menu kontekstowe (Add Child, Edit, Delete, View Readings)
- **Reset View**: Wraca do kontekstu wybranego węzła
- **Fit to Screen**: Dopasowuje widok do wszystkich węzłów

### Filtry w Tree View

- Zaznacz/odznacz typy węzłów (Meters/Distribution/Consumers)
- Pasujące węzły są podświetlone
- Niepasujące są przyciemnione (opacity 40%)

### Dodawanie Odczytów

1. Prawym przyciskiem na licznik → **"View Readings"**
2. W modalu wypełnij formularz nowego odczytu
3. Wartości pojawią się w tabeli i na wykresie

### Export/Import Projektu

**Export:**
1. Na stronie głównej lub w projekcie kliknij **"Export"**
2. Pobierze się plik JSON z całą strukturą

**Import:**
1. Strona główna → w kodzie projektu jest endpoint `/api/projects/import`
2. POST JSON z danymi projektu
3. Utworzy nowy projekt z zaimportowanymi danymi

## Zarządzanie Kategoriami

Przy tworzeniu węzła Consumer możesz dodawać nowe kategorie:
1. W dropdown "Category" wybierz **"+ Add New..."**
2. Wpisz nazwę nowej kategorii
3. Kategoria zostanie zapisana i będzie dostępna dla kolejnych węzłów

Domyślne kategorie:
- **Consumers**: Lighting, HVAC, Elevator, Pumps, Ventilation, Outlets
- **Meters**: Main, Submeter
- **Distribution**: Main Panel, Sub Panel

## Architektura Bazy Danych

### Neo4j
Każdy projekt ma własną bazę danych (`project_<uuid>`):

**Węzły:**
- `MeteringTree`: Root projektu
- `Meter`: Liczniki (properties: id, name, description, subtype, serial_number, location, installation_date)
- `Distribution`: Rozdzielnie
- `Consumer`: Odbiory (category zamiast subtype)

**Relacje:**
- `CONNECTED_TO`: Skierowana relacja rodzic→dziecko

### TimescaleDB

**Tabele:**
- `projects`: Metadane projektów
- `categories`: Kategorie/podtypy per projekt
- `readings`: Hypertable z odczytami (time, project_id, node_id, value, unit)
- `daily_readings`: Materialized view z agregatami dziennymi

## Troubleshooting

### Kontenery nie startują

```powershell
docker-compose down
docker-compose up --build
```

### Port zajęty

Zmień porty w `docker-compose.yml`:
```yaml
ports:
  - "5001:5000"  # Flask
  - "5433:5432"  # TimescaleDB
```

### Neo4j nie odpowiada

Sprawdź logi:
```powershell
docker-compose logs neo4j
```

Sprawdź czy ma wystarczająco pamięci (min 1GB heap):
```yaml
environment:
  - NEO4J_dbms_memory_heap_max__size=2G
```

### Błąd "database not found"

Neo4j Community 5.x wspiera multiple databases. Jeśli używasz starszej wersji, zaktualizuj do >=5.0 lub zmień na single-database mode.

### Import CSV failuje

Sprawdź:
- Plik jest UTF-8
- Kolumny zgodne z templatem
- `parent_name` musi wskazywać na istniejący węzeł
- `type` musi być jednym z: Meter, Distribution, Consumer

## Struktura Projektu

```
MeteringGraph/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── config.py             # Konfiguracja
│   ├── routes/               # API endpoints
│   │   ├── projects.py
│   │   ├── nodes.py
│   │   ├── graph.py
│   │   ├── readings.py
│   │   ├── categories.py
│   │   └── bulk.py
│   ├── services/             # Database services
│   │   ├── neo4j_service.py
│   │   └── timescale_service.py
│   └── utils/                # Utilities
│       └── csv_parser.py
├── templates/                # Jinja templates
│   ├── base.html
│   ├── index.html
│   ├── project.html
│   └── modals/
├── static/                   # Frontend assets
│   ├── css/main.css
│   ├── js/
│   │   ├── utils.js
│   │   ├── tree.js
│   │   ├── graph.js
│   │   └── modals.js
│   └── templates/
│       └── bulk_import_template.csv
├── docker-compose.yml
├── Dockerfile
├── init.sql                  # TimescaleDB init
├── requirements.txt
└── run.py                    # Entry point
```

## Komendy Docker

```powershell
# Start aplikacji
docker-compose up

# Start w tle
docker-compose up -d

# Stop aplikacji
docker-compose down

# Rebuild po zmianach
docker-compose up --build

# Zobacz logi
docker-compose logs -f

# Restart pojedynczego serwisu
docker-compose restart flask_app

# Usunięcie wszystkich danych (volumes)
docker-compose down -v
```

## Development

### Zmiany w kodzie Python
Kod jest montowany jako volume, więc zmiany są widoczne od razu (Flask w trybie debug).

### Zmiany w static/templates
Odśwież stronę w przeglądarce (Ctrl+F5).

### Zmiany w requirements.txt
```powershell
docker-compose up --build
```

## Bezpieczeństwo

**WAŻNE dla produkcji:**
1. Zmień hasła w `.env`:
   ```
   NEO4J_PASSWORD=twoje_silne_haslo
   POSTGRES_PASSWORD=twoje_silne_haslo
   SECRET_KEY=wygeneruj_losowy_klucz
   ```

2. Ustaw `FLASK_ENV=production`

3. Dodaj SSL/TLS dla Neo4j i PostgreSQL

4. Rozważ uwierzytelnianie użytkowników (obecnie single-user)

## Licencja

Internal project - all rights reserved.

## Kontakt

W razie problemów sprawdź logi: `docker-compose logs -f`
