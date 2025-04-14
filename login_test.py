import time
import sys
import os
import django
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Ustawiamy zmienną środowiskową dla Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ksiazkakucharska.settings')
django.setup()

# Podstawowe dane testowe
username = 'testuser'
password = 'TestUser123'

# Konfiguracja przeglądarki Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

# Inicjalizacja sterownika
driver = webdriver.Chrome(options=chrome_options)

try:
    # Logowanie użytkownika
    driver.get("http://localhost:8000/accounts/login/")
    print(f"Otworzono stronę logowania dla użytkownika {username}")
    
    # Zapisanie zrzutu ekranu strony logowania
    driver.save_screenshot("login_page.png")
    print("Zapisano zrzut ekranu strony logowania")
    
    # Wypełnienie formularza logowania
    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "id_username")))
    driver.find_element(By.ID, "id_username").send_keys(username)
    driver.find_element(By.ID, "id_password").send_keys(password)
    
    # Zapisanie zrzutu ekranu wypełnionego formularza
    driver.save_screenshot("filled_login_form.png")
    print("Zapisano zrzut ekranu wypełnionego formularza logowania")
    
    # Kliknięcie przycisku logowania
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    driver.execute_script("arguments[0].click();", submit_button)
    
    # Czekaj na przekierowanie po zalogowaniu
    time.sleep(2)
    
    # Sprawdź aktualny URL
    current_url = driver.current_url
    print(f"Po zalogowaniu przekierowano na: {current_url}")
    
    # Zapisanie zrzutu ekranu po zalogowaniu
    driver.save_screenshot("after_login.png")
    print("Zapisano zrzut ekranu strony po zalogowaniu")
    
    # Przejście do strony przepisów
    driver.get("http://localhost:8000/recipes/")
    print("Otworzono stronę z przepisami")
    
    # Czekaj na załadowanie strony
    time.sleep(2)
    
    # Zapisanie zrzutu ekranu strony z przepisami
    driver.save_screenshot("recipes_page.png")
    print("Zapisano zrzut ekranu strony z przepisami")
    
    # Sprawdź, czy strona z przepisami się załadowała
    print(f"Aktualny URL: {driver.current_url}")
    print(f"Tytuł strony: {driver.title}")
    
    # Sprawdź, czy są elementy charakterystyczne dla strony z przepisami
    recipe_elements = driver.find_elements(By.CSS_SELECTOR, ".card, .recipe-card, .recipe-item")
    print(f"Znaleziono {len(recipe_elements)} elementów przepisów na stronie")
    
except Exception as e:
    print(f"BŁĄD: {e}")
    # Zapisz zrzut ekranu w razie błędu
    driver.save_screenshot("error.png")
    print("Zapisano zrzut ekranu błędu")
finally:
    # Zakończenie testu
    driver.quit()
    print("Zamknięto przeglądarkę") 