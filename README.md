# Książka Kucharska

Aplikacja do zarządzania przepisami kulinarnymi z możliwością generowania list zakupów.

## Funkcje

- Dodawanie, edycja i usuwanie przepisów
- Dodawanie składników z jednostkami miary
- Przeliczanie jednostek miary
- Generowanie list zakupów
- Zarządzanie zawartością lodówki

## Wymagania

- Python 3.8+
- Django 4.2+
- Pozostałe zależności w pliku requirements.txt

## Instalacja

1. Sklonuj repozytorium:
```
git clone <adres-repozytorium>
cd ksiazkakucharska
```

2. Utwórz i aktywuj wirtualne środowisko:

Na Windows:
```
python -m venv venv
venv\Scripts\activate
```

Na Linux/Mac:
```
python3 -m venv venv
source venv/bin/activate
```

3. Zainstaluj zależności:
```
pip install -r requirements.txt
```

4. Wykonaj migracje bazy danych:
```
python manage.py migrate
```

5. Załaduj początkowe dane (kategorie przepisów, jednostki miary):
```
python manage.py loaddata recipes/fixtures/initial_categories.json
python manage.py loaddata recipes/fixtures/initial_units.json
```

6. Utwórz konto administratora:
```
python manage.py createsuperuser
```

## Uruchomienie

Uruchom serwer deweloperski:
```
python manage.py runserver
```

Aplikacja będzie dostępna pod adresem http://127.0.0.1:8000/

Panel administracyjny: http://127.0.0.1:8000/admin/

## Pierwsze kroki

1. Zaloguj się na utworzone konto użytkownika
2. Dodaj nowe składniki w sekcji "Składniki"
3. Dodaj nowy przepis w sekcji "Przepisy"
4. Przeglądaj przepisy i dodawaj je do ulubionych
5. Dodawaj składniki przepisów do listy zakupów

## Struktura projektu

- `recipes` - główna aplikacja do zarządzania przepisami
- `fridge` - aplikacja do zarządzania zawartością lodówki
- `shopping` - aplikacja do zarządzania listami zakupów
- `accounts` - aplikacja do zarządzania kontami użytkowników

## Funkcjonalności szczegółowo

### Zarządzanie przepisami
- Dodawanie nowych przepisów z wieloma składnikami
- Edycja i usuwanie własnych przepisów
- Przeglądanie przepisów innych użytkowników
- Filtrowanie przepisów według kategorii, składników, diety
- Wyszukiwanie przepisów po nazwie lub składnikach
- Skalowanie przepisów do wybranej liczby porcji
- Dodawanie przepisów do ulubionych
- Polubienia i komentarze do przepisów

### Zarządzanie składnikami i jednostkami miary
- Kategorie składników (np. mięso, nabiał, warzywa)
- Automatyczne przeliczanie jednostek miary (np. gramy na kilogramy)
- Konwersje między różnymi typami jednostek (np. gramy na mililitry) z wykorzystaniem gęstości składników
- Konwersje jednostek specyficzne dla składnika (np. sztuki na gramy)

### Zarządzanie lodówką
- Dodawanie składników do wirtualnej lodówki
- Śledzenie ilości i dat ważności produktów
- Automatyczne sprawdzanie, czy przepis może być przygotowany z dostępnych składników
- Oznaczanie składników jako zużyte podczas przygotowywania przepisu

### Zarządzanie listami zakupów
- Tworzenie list zakupów
- Automatyczne dodawanie brakujących składników do listy
- Oznaczanie zakupionych produktów
- Dodawanie produktów do lodówki po zakupach

## Licencja

Wszystkie prawa zastrzeżone.
