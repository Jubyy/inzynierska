import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_submit_ingredient():
    """
    Test sprawdzający funkcjonalność zgłaszania nowego składnika
    z prawidłową tablicą konwersji.
    """
    # Konfiguracja przeglądarki Chrome w trybie headless
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Inicjalizacja sterownika
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)
    
    try:
        # Przejście do strony logowania
        driver.get("http://localhost:8000/accounts/login/")
        print("Otworzono stronę logowania")
        
        # Logowanie
        wait.until(EC.presence_of_element_located((By.ID, "id_username")))
        driver.find_element(By.ID, "id_username").send_keys("admin")
        driver.find_element(By.ID, "id_password").send_keys("admin123")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        print("Zalogowano się jako admin")
        
        # Przejście do strony zgłaszania produktu
        driver.get("http://localhost:8000/recipes/ingredient/submit/")
        print("Otworzono stronę zgłaszania składnika")
        
        # Sprawdzenie, czy formularz się załadował
        wait.until(EC.presence_of_element_located((By.ID, "id_name")))
        print("Formularz zgłaszania składnika został załadowany")
        
        # Sprawdzenie, czy istnieje pole wyboru tablicy konwersji
        conversion_table_select = driver.find_element(By.ID, "id_conversion_table")
        if conversion_table_select:
            print("Pole wyboru tablicy konwersji istnieje")
            options = conversion_table_select.find_elements(By.TAG_NAME, "option")
            print(f"Liczba dostępnych tablic konwersji: {len(options)}")
        else:
            print("BŁĄD: Nie znaleziono pola wyboru tablicy konwersji")
        
        # Wypełnianie formularza
        driver.find_element(By.ID, "id_name").send_keys("Składnik Testowy")
        driver.find_element(By.ID, "id_description").send_keys("Opis testowego składnika")
        
        # Wybór kategorii
        category_select = driver.find_element(By.ID, "id_category")
        category_options = category_select.find_elements(By.TAG_NAME, "option")
        if len(category_options) > 1:
            category_options[1].click()
            print(f"Wybrano kategorię: {category_options[1].text}")
        
        # Wybór tablicy konwersji (opcja pierwsza niebędąca pustą)
        conversion_options = conversion_table_select.find_elements(By.TAG_NAME, "option")
        if len(conversion_options) > 1:
            conversion_options[1].click()
            print(f"Wybrano tablicę konwersji: {conversion_options[1].text}")
        
        # Zrzut ekranu wypełnionego formularza
        driver.save_screenshot("form_filled.png")
        print("Zapisano zrzut ekranu wypełnionego formularza")
        
        # Wysłanie formularza
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        print("Kliknięto przycisk wysyłania formularza")
        
        # Sprawdzenie, czy formularz został wysłany
        time.sleep(2)  # Krótkie oczekiwanie na przetworzenie
        current_url = driver.current_url
        print(f"Przekierowano do: {current_url}")
        
        # Sprawdzenie, czy wyświetlił się komunikat o sukcesie
        success_messages = driver.find_elements(By.CLASS_NAME, "alert-success")
        if success_messages:
            print(f"Komunikat sukcesu: {success_messages[0].text}")
        else:
            print("Brak komunikatu sukcesu - możliwy błąd w przetwarzaniu")
            error_messages = driver.find_elements(By.CLASS_NAME, "alert-danger")
            if error_messages:
                print(f"Komunikat błędu: {error_messages[0].text}")
        
        # Sprawdzenie panelu administratora oczekujących składników
        driver.get("http://localhost:8000/recipes/admin/pending-ingredients/")
        print("Sprawdzanie panelu administratora z oczekującymi składnikami")
        
        time.sleep(1)
        driver.save_screenshot("admin_panel.png")
        print("Zapisano zrzut ekranu panelu administratora")
        
        return True
        
    except Exception as e:
        print(f"BŁĄD podczas testu: {e}")
        driver.save_screenshot("error.png")
        print("Zapisano zrzut ekranu błędu")
        return False
        
    finally:
        driver.quit()
        print("Zamknięto przeglądarkę")

if __name__ == "__main__":
    print("Rozpoczęcie testu zgłaszania składnika")
    result = test_submit_ingredient()
    print(f"Test zakończony {'powodzeniem' if result else 'niepowodzeniem'}")
    sys.exit(0 if result else 1) 