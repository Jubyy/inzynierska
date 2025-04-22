# Instrukcja wdrożenia aplikacji na PythonAnywhere

## 1. Konfiguracja projektu

### 1.1. Klonowanie repozytorium
```bash
# Przejdź do katalogu domowego na PythonAnywhere
cd ~

# Sklonuj repozytorium
git clone [URL_TWOJEGO_REPOZYTORIUM] ksiazkakucharska
cd ksiazkakucharska
```

### 1.2. Utworzenie wirtualnego środowiska i instalacja zależności
```bash
# Utwórz wirtualne środowisko
mkvirtualenv --python=/usr/bin/python3.10 ksiazkakucharska-env

# Aktywuj środowisko (jeśli nie jest aktywne)
workon ksiazkakucharska-env

# Zainstaluj wymagane pakiety
pip install -r requirements.txt
```

## 2. Konfiguracja bazy danych

### 2.1. Utworzenie bazy danych MySQL
- Przejdź do zakładki "Databases" w panelu PythonAnywhere
- Utwórz nową bazę danych MySQL - zanotuj nazwę, użytkownika i hasło

### 2.2. Dostosowanie ustawień Django

Utwórz plik `ksiazkakucharska/settings_pa.py` z ustawieniami dla PythonAnywhere:

```python
from .settings import *

# Ustawienia bezpieczeństwa
DEBUG = False
SECRET_KEY = 'twój_tajny_klucz'  # Zmień na bezpieczny, unikalny ciąg znaków
ALLOWED_HOSTS = ['twojanazwa.pythonanywhere.com']

# Baza danych - dostosuj ustawienia do swoich danych
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'twojanazwa$ksiazkakucharska',
        'USER': 'twojanazwa',
        'PASSWORD': 'twoje_haslo',
        'HOST': 'twojanazwa.mysql.pythonanywhere-services.com',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Statyczne pliki i media
STATIC_URL = '/static/'
STATIC_ROOT = '/home/twojanazwa/ksiazkakucharska/static'
MEDIA_URL = '/media/'
MEDIA_ROOT = '/home/twojanazwa/ksiazkakucharska/media'

# Email (opcjonalnie - jeśli potrzebujesz wysyłać emaile)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # lub inny serwer SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'twój_email@example.com'
EMAIL_HOST_PASSWORD = 'twoje_hasło'

# Dodanie WhiteNoise do obsługi plików statycznych
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Dodanie Crispy Forms
INSTALLED_APPS += [
    'crispy_forms',
    'crispy_bootstrap4',
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'
```

## 3. Migracja bazy danych i kolekcja plików statycznych

```bash
# Aktywuj wirtualne środowisko
workon ksiazkakucharska-env

# Przejdź do katalogu projektu
cd ~/ksiazkakucharska

# Ustaw odpowiedni moduł ustawień
export DJANGO_SETTINGS_MODULE=ksiazkakucharska.settings_pa

# Wykonaj migracje
python manage.py migrate

# Zbierz pliki statyczne
python manage.py collectstatic

# Utwórz superużytkownika
python manage.py createsuperuser
```

## 4. Konfiguracja aplikacji webowej w PythonAnywhere

### 4.1. Skonfiguruj nową aplikację webową:
- Przejdź do zakładki "Web" w panelu PythonAnywhere
- Kliknij "Add a new web app"
- Wybierz "Manual configuration"
- Wybierz Python 3.10
- W sekcji "Code" ustaw:
  - Source code: `/home/twojanazwa/ksiazkakucharska`
  - Working directory: `/home/twojanazwa/ksiazkakucharska`
  - WSGI configuration file: Kliknij na ścieżkę do pliku i wprowadź poniższe zmiany

### 4.2. Edytuj plik WSGI:
```python
import os
import sys

# Dodaj ścieżkę do projektu
path = '/home/twojanazwa/ksiazkakucharska'
if path not in sys.path:
    sys.path.append(path)

# Ustaw zmienną środowiskową wskazującą na właściwy plik ustawień
os.environ['DJANGO_SETTINGS_MODULE'] = 'ksiazkakucharska.settings_pa'

# Importuj aplikację Django
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 4.3. Skonfiguruj wirtualne środowisko:
- W sekcji "Virtualenv" wpisz: `/home/twojanazwa/.virtualenvs/ksiazkakucharska-env`

### 4.4. Skonfiguruj ścieżki statyczne:
- W sekcji "Static files" dodaj:
  - URL: `/static/`
  - Directory: `/home/twojanazwa/ksiazkakucharska/static`
  - URL: `/media/`
  - Directory: `/home/twojanazwa/ksiazkakucharska/media`

### 4.5. Skonfiguruj zmienne środowiskowe (opcjonalnie):
- W sekcji "Environment variables" możesz dodać dodatkowe zmienne środowiskowe, jeśli są potrzebne

## 5. Uruchom aplikację

- Kliknij przycisk "Reload" w zakładce "Web"
- Odwiedź swoją stronę pod adresem: `https://twojanazwa.pythonanywhere.com`

## 6. Dodatkowe wskazówki

### 6.1. Aktualizacja aplikacji z repozytorium Git
```bash
cd ~/ksiazkakucharska
git pull
workon ksiazkakucharska-env
python manage.py migrate
python manage.py collectstatic
```

Następnie kliknij "Reload" w zakładce "Web" na PythonAnywhere.

### 6.2. Pliki mediów
Upewnij się, że utworzyłeś katalog dla mediów i nadałeś mu odpowiednie uprawnienia:
```bash
mkdir -p ~/ksiazkakucharska/media
chmod 755 ~/ksiazkakucharska/media
```

### 6.3. Logi
Jeśli aplikacja nie działa poprawnie, sprawdź logi błędów w zakładce "Web" -> "Error log". 