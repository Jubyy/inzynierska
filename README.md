# Książka Kucharska - Twoja Wirtualna Asystentka Kulinarna

Książka Kucharska to kompleksowa aplikacja webowa stworzona w Django, która pomaga użytkownikom zarządzać przepisami, planować posiłki w oparciu o dostępne składniki oraz optymalizować zakupy spożywcze. Aplikacja łączy funkcjonalności tradycyjnej książki kucharskiej z nowoczesnym systemem zarządzania zapasami kuchennymi i inteligentnym generowaniem list zakupów.

## Główne funkcjonalności

### Zarządzanie przepisami 🍽️
- **Przepisy osobiste i społecznościowe**: tworzenie własnych przepisów i dostęp do publicznych przepisów innych użytkowników
- **Szczegółowe informacje**: czas przygotowania, poziom trudności, liczba porcji, zdjęcia
- **Inteligentna klasyfikacja diet**: automatyczne oznaczanie przepisów jako wegetariańskie, wegańskie lub mięsne
- **Wyszukiwanie i filtrowanie**: według kategorii, składników, diet i dostępności składników
- **Skalowanie porcji**: dynamiczne przeliczanie ilości składników dla różnej liczby porcji
- **Interakcje społecznościowe**: polubienia, dodawanie do ulubionych, komentarze do przepisów

### Wirtualna lodówka 🧊
- **Inwentaryzacja produktów**: zarządzanie dostępnymi składnikami i ich ilościami
- **Śledzenie terminów ważności**: monitoring dat przydatności produktów
- **Inteligentne dopasowanie przepisów**: wyszukiwanie przepisów, które można przygotować z dostępnych składników
- **Automatyczne aktualizacje**: odejmowanie zużytych składników po przygotowaniu przepisu

### Inteligentne listy zakupów 🛒
- **Automatyczne generowanie**: tworzenie list zakupów na podstawie brakujących składników
- **Niestandardowe listy**: możliwość ręcznego dodawania produktów
- **Oznaczanie zakupionych produktów**: kontrola nad postępem zakupów
- **Integracja z lodówką**: automatyczne dodawanie zakupionych produktów do wirtualnej lodówki

### System konwersji jednostek 📏
- **Uniwersalne przeliczniki**: automatyczna konwersja między różnymi jednostkami miary
- **Inteligentne konwersje**: uwzględnianie gęstości składników przy przeliczaniu między wagą a objętością
- **Jednostki specyficzne dla składników**: obsługa sztuk, opakowań i innych niestandardowych jednostek

### Personalizacja i zarządzanie kontami 👤
- **Profile użytkowników**: osobiste konta z preferencjami i historią
- **Panel administracyjny**: zaawansowane zarządzanie zawartością dla administratorów
- **Responsywny interfejs**: dostosowany do komputerów i urządzeń mobilnych

## Korzyści dla użytkowników

- **Oszczędność czasu**: szybkie planowanie posiłków i zakupów
- **Redukcja marnowania żywności**: lepsze zarządzanie zapasami i datami ważności
- **Optymalizacja zakupów**: kupowanie tylko tego, co naprawdę potrzebne
- **Inspiracja kulinarna**: odkrywanie nowych przepisów dopasowanych do preferencji
- **Adaptacja do różnych diet**: łatwe filtrowanie przepisów dla określonych preferencji żywieniowych
- **Precyzyjne gotowanie**: dokładne przeliczanie ilości składników dla różnej liczby porcji

## Technologie

- **Backend**: Python, Django, SQLite/PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **Narzędzia**: Django ORM, Django Forms, Django Templates
- **Testy**: Unittest, Django Test Client

## Instalacja i uruchomienie

### Wymagania
- Python 3.8+
- Django 4.2+
- Pozostałe zależności w pliku requirements.txt

### Szybka instalacja

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

5. Załaduj początkowe dane:
```
python manage.py loaddata recipes/fixtures/initial_categories.json
python manage.py loaddata recipes/fixtures/initial_units.json
```

6. Utwórz konto administratora:
```
python manage.py createsuperuser
```

7. Uruchom serwer deweloperski:
```
python manage.py runserver
```

Aplikacja będzie dostępna pod adresem http://127.0.0.1:8000/

## Struktura projektu

- **recipes**: główna aplikacja do zarządzania przepisami
- **fridge**: aplikacja do zarządzania zawartością lodówki
- **shopping**: aplikacja do zarządzania listami zakupów
- **accounts**: aplikacja do zarządzania kontami użytkowników

## Przykładowy przepływ pracy

1. Zarejestruj się i zaloguj na swoje konto
2. Dodaj składniki do swojej wirtualnej lodówki
3. Przeglądaj przepisy, które możesz przygotować z dostępnych składników
4. Wybierz przepis i dostosuj liczbę porcji
5. Wygeneruj listę zakupów dla brakujących składników
6. Po zakupach, oznacz produkty jako zakupione i dodaj je do lodówki
7. Przygotuj wybrany przepis, a zużyte składniki zostaną automatycznie odjęte z lodówki

## Licencja

Wszystkie prawa zastrzeżone.

## Autorzy

- Imię Nazwisko
- Kontakt: email@example.com
