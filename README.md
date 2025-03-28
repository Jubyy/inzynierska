# Książka Kucharska z bazą danych zawartości lodówki

Aplikacja internetowa do zarządzania przepisami, składnikami i zawartością lodówki. Pozwala na śledzenie dostępnych składników, wyszukiwanie przepisów na ich podstawie oraz planowanie zakupów.

## Autorzy
- Filip Żywica

## Funkcjonalności

- 👤 **Zarządzanie kontem użytkownika**: rejestracja, logowanie, edycja profilu, resetowanie hasła
- 📝 **Zarządzanie przepisami**: dodawanie, przeglądanie, edycja, usuwanie przepisów
- 🥗 **Kategoryzacja przepisów**: kategorie przepisów (np. obiad, deser), automatyczne oznaczanie jako wegetariańskie/wegańskie
- ⚖️ **Skalowanie przepisów**: dostosowanie ilości składników do liczby porcji
- 🔄 **Konwersja jednostek**: automatyczna konwersja między różnymi jednostkami miary
- 🧊 **Zarządzanie zawartością lodówki**: dodawanie, usuwanie, aktualizacja produktów
- 🔍 **Wyszukiwanie przepisów**: po nazwie, składnikach, kategoriach
- 🛒 **Listy zakupów**: tworzenie list zakupów na podstawie przepisów lub brakujących składników
- 📊 **Planowanie posiłków**: oznaczanie przepisów jako przygotowanych i automatyczne usuwanie zużytych składników z lodówki

## Wymagania techniczne

- Python 3.8+
- Django 4.2+
- Pillow (do obsługi obrazów)
- Bootstrap 5 (UI)

## Instalacja i uruchomienie

1. Sklonuj repozytorium:
```bash
git clone <adres-repozytorium>
cd praca_inzynierska
```

2. Utwórz i aktywuj wirtualne środowisko:
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

3. Zainstaluj wymagane zależności:
```bash
pip install -r requirements.txt
```

4. Wykonaj migracje bazy danych:
```bash
python manage.py makemigrations
python manage.py migrate
```

5. (Opcjonalnie) Zainicjalizuj bazę danych przykładowymi danymi:
```bash
python manage.py initialize_db
```

6. Uruchom serwer deweloperski:
```bash
python manage.py runserver
```

7. Otwórz przeglądarkę i przejdź do http://127.0.0.1:8000

## Domyślne konto administratora (po inicjalizacji bazy danych)

- Login: admin
- Hasło: admin

## Struktura projektu

- `accounts/` - aplikacja do zarządzania kontami użytkowników
- `recipes/` - aplikacja do zarządzania przepisami
- `fridge/` - aplikacja do zarządzania zawartością lodówki
- `shopping/` - aplikacja do zarządzania listami zakupów
- `static/` - pliki statyczne (CSS, JavaScript, obrazy)
- `media/` - pliki multimedialne przesyłane przez użytkowników (zdjęcia przepisów, avatary)
- `templates/` - szablony HTML

## Licencja

Wszystkie prawa zastrzeżone.
