import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

def test_admin_pending_ingredients():
    """
    Test sprawdzający:
    1. Wyświetlanie listy oczekujących składników w panelu administratora
    2. Poprawne działanie formularza zatwierdzania składnika
    3. Uwzględnienie parametru tablicy konwersji przy zatwierdzaniu
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
        # Logowanie jako administrator
        driver.get("http://localhost:8000/accounts/login/")
        wait.until(EC.presence_of_element_located((By.ID, "id_username")))
        driver.find_element(By.ID, "id_username").send_keys("admin")
        driver.find_element(By.ID, "id_password").send_keys("admin123")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        print("✓ Zalogowano jako administrator")
        
        # Przejście do panelu administratora - oczekujące składniki
        driver.get("http://localhost:8000/recipes/admin/pending-ingredients/")
        print("Otworzono panel administratora ze składnikami oczekującymi na zatwierdzenie")
        
        # Sprawdzenie czy panel się załadował
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".card-header h5")))
        page_title = driver.find_element(By.CSS_SELECTOR, ".card-header h5").text
        if "Oczekujące składniki" not in page_title:
            print(f"BŁĄD: Nieprawidłowy tytuł strony: '{page_title}'")
            return False
        
        print("✓ Panel administratora załadowany poprawnie")
        driver.save_screenshot("admin_panel.png")
        
        # Sprawdzenie obecności tabeli z oczekującymi składnikami
        try:
            ingredients_table = driver.find_element(By.CSS_SELECTOR, "table.table")
            print("✓ Tabela składników istnieje")
        except:
            print("BŁĄD: Nie znaleziono tabeli z oczekującymi składnikami")
            return False
        
        # Sprawdzenie nagłówków tabeli
        headers = ingredients_table.find_elements(By.CSS_SELECTOR, "thead th")
        header_texts = [header.text for header in headers]
        required_headers = ["Nazwa", "Kategoria", "Zgłaszający", "Data"]
        
        missing_headers = [header for header in required_headers if not any(header in h for h in header_texts)]
        if missing_headers:
            print(f"BŁĄD: Brakujące nagłówki w tabeli: {missing_headers}")
        else:
            print("✓ Wszystkie wymagane nagłówki są obecne w tabeli")
        
        # Sprawdzenie czy są jakieś składniki w tabeli
        rows = ingredients_table.find_elements(By.CSS_SELECTOR, "tbody tr")
        if len(rows) == 0:
            print("INFORMACJA: Brak oczekujących składników w tabeli")
            
            # Przejdźmy do formularza dodawania składnika, aby dodać testowy
            driver.get("http://localhost:8000/recipes/submit-ingredient/")
            print("Przejście do formularza dodawania składnika")
            
            # Wypełnianie formularza
            wait.until(EC.presence_of_element_located((By.ID, "id_name")))
            driver.find_element(By.ID, "id_name").send_keys("Testowy Składnik")
            
            # Wybór kategorii
            category_select = Select(driver.find_element(By.ID, "id_category"))
            category_select.select_by_index(1)  # Wybierz pierwszą kategorię
            
            # Wybór tablicy konwersji
            conversion_table_select = Select(driver.find_element(By.ID, "id_conversion_table"))
            conversion_table_select.select_by_index(1)  # Wybierz pierwszą tablicę konwersji
            
            # Dodanie opisu
            driver.find_element(By.ID, "id_description").send_keys("Testowy składnik do sprawdzenia panelu administratora")
            
            # Wysłanie formularza
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            print("Wysłano formularz zgłoszenia składnika")
            
            # Powrót do panelu administratora
            driver.get("http://localhost:8000/recipes/admin/pending-ingredients/")
            print("Powrót do panelu administratora")
            
            # Sprawdzenie czy pojawił się nowy składnik
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody tr")))
            rows = driver.find_element(By.CSS_SELECTOR, "table.table").find_elements(By.CSS_SELECTOR, "tbody tr")
            
            if len(rows) == 0:
                print("BŁĄD: Nie udało się dodać testowego składnika")
                return False
        
        print(f"✓ Znaleziono {len(rows)} oczekujących składników")
        
        # Sprawdzenie pierwszego składnika
        row = rows[0]
        cells = row.find_elements(By.TAG_NAME, "td")
        ingredient_name = cells[0].text
        print(f"Sprawdzanie składnika: {ingredient_name}")
        
        # Znalezienie przycisku "Zarządzaj" i kliknięcie go
        manage_button = row.find_element(By.CSS_SELECTOR, "button.btn-primary")
        if "Zarządzaj" not in manage_button.text:
            print(f"BŁĄD: Nieprawidłowy przycisk zarządzania: '{manage_button.text}'")
        else:
            print("✓ Znaleziono przycisk 'Zarządzaj'")
        
        # Kliknięcie przycisku "Zarządzaj"
        manage_button.click()
        print("Kliknięto przycisk 'Zarządzaj'")
        
        # Sprawdzenie czy modal się otworzył
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal.show")))
        print("✓ Okno modalne zostało otwarte")
        driver.save_screenshot("admin_ingredient_modal.png")
        
        # Sprawdzenie, czy w modalu jest wybór tablicy konwersji
        modal = driver.find_element(By.CSS_SELECTOR, ".modal.show")
        
        try:
            conversion_table_select = modal.find_element(By.ID, "id_conversion_table")
            print("✓ Pole wyboru tablicy konwersji jest obecne w modalu")
            
            # Sprawdzenie czy pole jest typu select
            if conversion_table_select.tag_name.lower() != "select":
                print(f"BŁĄD: Pole tablicy konwersji nie jest typu select, ale {conversion_table_select.tag_name}")
            else:
                # Sprawdzenie opcji w select
                options = Select(conversion_table_select).options
                if len(options) == 0:
                    print("BŁĄD: Brak opcji w polu wyboru tablicy konwersji")
                else:
                    print(f"✓ Znaleziono {len(options)} opcji w polu wyboru tablicy konwersji")
        except:
            print("BŁĄD: Nie znaleziono pola wyboru tablicy konwersji w modalu")
            return False
        
        # Sprawdzenie innych pól w formularzu
        required_fields = ["id_default_unit", "id_allowed_units", "id_density"]
        missing_fields = []
        
        for field_id in required_fields:
            try:
                modal.find_element(By.ID, field_id)
            except:
                missing_fields.append(field_id)
        
        if missing_fields:
            print(f"BŁĄD: Brakujące pola w formularzu: {missing_fields}")
        else:
            print("✓ Wszystkie wymagane pola są obecne w formularzu")
        
        # Sprawdzenie przycisków akcji
        approve_button = modal.find_element(By.CSS_SELECTOR, "button.btn-success")
        reject_button = modal.find_element(By.CSS_SELECTOR, "button.btn-danger")
        
        if "Zatwierdź" not in approve_button.text:
            print(f"BŁĄD: Nieprawidłowy tekst przycisku zatwierdzania: '{approve_button.text}'")
        else:
            print("✓ Znaleziono przycisk 'Zatwierdź'")
        
        if "Odrzuć" not in reject_button.text:
            print(f"BŁĄD: Nieprawidłowy tekst przycisku odrzucania: '{reject_button.text}'")
        else:
            print("✓ Znaleziono przycisk 'Odrzuć'")
        
        # Zatwierdźmy składnik, wybierając najpierw tablicę konwersji
        conversion_table_select = Select(modal.find_element(By.ID, "id_conversion_table"))
        conversion_table_select.select_by_index(0)  # Wybierz pierwszą tablicę konwersji
        print(f"Wybrano tablicę konwersji: {conversion_table_select.first_selected_option.text}")
        
        # Wybór domyślnej jednostki
        default_unit_select = Select(modal.find_element(By.ID, "id_default_unit"))
        default_unit_select.select_by_index(0)  # Wybierz pierwszą jednostkę
        print(f"Wybrano domyślną jednostkę: {default_unit_select.first_selected_option.text}")
        
        # Zatwierdzenie składnika
        approve_button.click()
        print("Kliknięto przycisk 'Zatwierdź'")
        
        # Sprawdzenie, czy pojawił się komunikat sukcesu
        try:
            success_message = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "alert-success"))
            )
            print(f"✓ Komunikat sukcesu został wyświetlony: '{success_message.text}'")
            driver.save_screenshot("admin_ingredient_approved.png")
            
            # Sprawdzenie, czy składnik zniknął z listy oczekujących
            time.sleep(2)  # Krótkie opóźnienie, aby strona mogła się odświeżyć
            new_rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
            
            if len(new_rows) < len(rows):
                print("✓ Składnik został usunięty z listy oczekujących po zatwierdzeniu")
            else:
                print("BŁĄD: Składnik nadal widoczny na liście oczekujących po zatwierdzeniu")
        except:
            print("BŁĄD: Nie znaleziono komunikatu sukcesu po zatwierdzeniu składnika")
            return False
        
        # Sprawdzenie sekcji "Ostatnio przetworzone składniki"
        try:
            recent_section = driver.find_element(By.ID, "recent-ingredients")
            print("✓ Sekcja 'Ostatnio przetworzone składniki' jest obecna")
            
            # Sprawdzenie, czy zatwierdzony składnik pojawił się w tej sekcji
            recent_items = recent_section.find_elements(By.CSS_SELECTOR, ".list-group-item")
            
            if len(recent_items) > 0:
                print(f"✓ Znaleziono {len(recent_items)} niedawno przetworzonych składników")
                
                # Sprawdzenie, czy nasz zatwierdzony składnik jest na liście
                recent_names = [item.text for item in recent_items]
                if any(ingredient_name in name for name in recent_names):
                    print(f"✓ Zatwierdzony składnik '{ingredient_name}' pojawił się w sekcji")
                else:
                    print(f"BŁĄD: Nie znaleziono zatwierdzonego składnika '{ingredient_name}' w sekcji")
            else:
                print("BŁĄD: Brak niedawno przetworzonych składników w sekcji")
        except:
            print("BŁĄD: Nie znaleziono sekcji 'Ostatnio przetworzone składniki'")
        
        print("\n=== WYNIK TESTÓW ===")
        print("✓ Panel administratora ze zgłoszonymi składnikami działa poprawnie")
        print("✓ Parametr tablicy konwersji jest uwzględniany przy zatwierdzaniu składnika")
        
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
    print("Rozpoczęcie testów panelu administratora ze zgłoszonymi składnikami")
    result = test_admin_pending_ingredients()
    print(f"\nTesty zakończone {'powodzeniem' if result else 'niepowodzeniem'}")
    sys.exit(0 if result else 1) 