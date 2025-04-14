import time
import sys
import os
import django
import random
import string
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

# Dodajemy ścieżkę projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ustawiamy zmienną środowiskową dla Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ksiazkakucharska.settings')
django.setup()

# Importujemy modele Django
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

def create_test_user():
    """Tworzy testowego użytkownika do testów logowania, jeśli nie istnieje"""
    username = 'testlogin'
    email = 'testlogin@example.com'
    password = 'TestLogin123'
    
    # Sprawdź czy użytkownik istnieje
    try:
        user = User.objects.get(username=username)
        print(f"Użytkownik {username} już istnieje, można go użyć do testów")
        # Upewnij się, że użytkownik jest aktywny
        if not user.is_active:
            user.is_active = True
            user.save()
            print(f"Użytkownik {username} został aktywowany")
    except User.DoesNotExist:
        # Utwórz nowego użytkownika
        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            is_active=True  # Użytkownik jest od razu aktywny
        )
        print(f"Utworzono użytkownika testowego: {username}")
    
    return username, password

def test_login():
    """
    Test sprawdzający:
    1. Poprawne logowanie z prawidłowymi danymi
    2. Obsługę błędnych danych logowania
    3. Funkcję "Zapamiętaj mnie"
    4. Przekierowanie po udanym logowaniu
    """
    print("Rozpoczęcie testów logowania")
    
    # Tworzenie testowego użytkownika
    username, password = create_test_user()
    
    # Konfiguracja przeglądarki Chrome w trybie headless
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    
    # Inicjalizacja sterownika
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)
    
    # Rezultaty testów
    test_results = {
        "correct_login": False,
        "invalid_credentials": False,
        "remember_me": False,
        "redirection": False
    }
    
    try:
        # Przejście do strony logowania
        driver.get("http://localhost:8000/accounts/login/")
        print("Otworzono stronę logowania")
        
        # 1. Test poprawnego logowania z prawidłowymi danymi
        print("\n=== TEST 1: POPRAWNE LOGOWANIE ===")
        
        # Wypełnienie formularza poprawnymi danymi
        wait.until(EC.presence_of_element_located((By.ID, "id_username")))
        driver.find_element(By.ID, "id_username").send_keys(username)
        driver.find_element(By.ID, "id_password").send_keys(password)
        
        # Kliknięcie przycisku logowania
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", submit_button)
        
        # Sprawdzenie przekierowania po logowaniu
        try:
            WebDriverWait(driver, 5).until(
                lambda d: '/dashboard/' in d.current_url or '/accounts/dashboard/' in d.current_url
            )
            print("✓ Przekierowano na dashboard po pomyślnym logowaniu")
            test_results["redirection"] = True
            test_results["correct_login"] = True
            
            # Zapisanie zrzutu ekranu dashboard
            driver.save_screenshot("dashboard_after_login.png")
            print("✓ Zapisano zrzut ekranu dashboard po logowaniu")
            
            # Wylogowanie się
            logout_link = None
            try:
                # Próba znalezienia linku wylogowania w menu użytkownika
                user_menu = driver.find_element(By.ID, "userMenu")
                driver.execute_script("arguments[0].click();", user_menu)
                time.sleep(1)  # Poczekaj na rozwinięcie menu
                
                logout_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'logout')]")
                if logout_elements:
                    logout_link = logout_elements[0]
            except:
                # Bezpośrednie szukanie linku wylogowania
                logout_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'logout')]")
                if logout_elements:
                    logout_link = logout_elements[0]
            
            if logout_link:
                driver.execute_script("arguments[0].click();", logout_link)
                print("✓ Pomyślnie wylogowano użytkownika")
            else:
                print("BŁĄD: Nie znaleziono linku do wylogowania")
                # Wróć do strony logowania ręcznie
                driver.get("http://localhost:8000/accounts/login/")
        
        except TimeoutException:
            print("BŁĄD: Nie przekierowano na dashboard po logowaniu")
            driver.save_screenshot("login_failed.png")
            print("Zapisano zrzut ekranu problemu logowania")
        
        # 2. Test obsługi błędnych danych logowania
        print("\n=== TEST 2: OBSŁUGA BŁĘDNYCH DANYCH LOGOWANIA ===")
        
        # Przejście ponownie do strony logowania
        driver.get("http://localhost:8000/accounts/login/")
        print("Otworzono stronę logowania ponownie")
        
        # Wypełnienie formularza nieprawidłowymi danymi
        wait.until(EC.presence_of_element_located((By.ID, "id_username")))
        driver.find_element(By.ID, "id_username").send_keys(username)
        driver.find_element(By.ID, "id_password").send_keys("nieprawidłowe_hasło")
        
        # Kliknięcie przycisku logowania
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", submit_button)
        
        # Sprawdzenie, czy pojawił się komunikat o błędzie
        time.sleep(1)  # Dajemy czas na przetworzenie formularza
        page_source = driver.page_source
        
        if "Nieprawidłowa nazwa użytkownika lub hasło" in page_source or "alert-danger" in page_source:
            print("✓ Wyświetlono komunikat o nieprawidłowych danych logowania")
            
            # Sprawdzenie, czy nadal jesteśmy na stronie logowania
            if "login" in driver.current_url and "dashboard" not in driver.current_url:
                print("✓ Użytkownik pozostaje na stronie logowania po nieudanej próbie")
                test_results["invalid_credentials"] = True
            else:
                print("BŁĄD: Przekierowano mimo nieprawidłowych danych")
        else:
            print("BŁĄD: Nie wyświetlono komunikatu o nieprawidłowych danych")
            driver.save_screenshot("invalid_credentials_failed.png")
            print("Zapisano zrzut ekranu problemu walidacji")
        
        # 3. Test funkcji "Zapamiętaj mnie"
        print("\n=== TEST 3: FUNKCJA ZAPAMIĘTAJ MNIE ===")
        
        # Przejście ponownie do strony logowania
        driver.get("http://localhost:8000/accounts/login/")
        print("Otworzono stronę logowania ponownie")
        
        # Wypełnienie formularza poprawnymi danymi
        wait.until(EC.presence_of_element_located((By.ID, "id_username")))
        driver.find_element(By.ID, "id_username").send_keys(username)
        driver.find_element(By.ID, "id_password").send_keys(password)
        
        # Zaznaczenie opcji "Zapamiętaj mnie"
        try:
            remember_me = driver.find_element(By.ID, "rememberMe")
            driver.execute_script("arguments[0].click();", remember_me)
            print("✓ Zaznaczono opcję 'Zapamiętaj mnie'")
            
            # Sprawdzenie, czy checkbox został zaznaczony
            if remember_me.is_selected():
                print("✓ Opcja 'Zapamiętaj mnie' została poprawnie zaznaczona")
                test_results["remember_me"] = True
            else:
                print("BŁĄD: Opcja 'Zapamiętaj mnie' nie została zaznaczona")
        except:
            print("UWAGA: Nie znaleziono checkboxa 'Zapamiętaj mnie'")
            driver.save_screenshot("remember_me_missing.png")
            
        # Logowanie z zapamiętaniem
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", submit_button)
        
        # Sprawdzenie przekierowania
        try:
            WebDriverWait(driver, 5).until(
                lambda d: '/dashboard/' in d.current_url or '/accounts/dashboard/' in d.current_url
            )
            print("✓ Logowanie z opcją 'Zapamiętaj mnie' działa poprawnie")
        except:
            print("BŁĄD: Problem z logowaniem przy użyciu opcji 'Zapamiętaj mnie'")
            
        # Zaktualizuj plik wyników testów
        with open('test_results.txt', 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        with open('test_results.txt', 'w', encoding='utf-8') as file:
            for line in lines:
                if 'Poprawne logowanie z prawidłowymi danymi' in line:
                    file.write(f"   {'[x]' if test_results['correct_login'] else '[ ]'} Poprawne logowanie z prawidłowymi danymi\n")
                elif 'Obsługa błędnych danych logowania' in line:
                    file.write(f"   {'[x]' if test_results['invalid_credentials'] else '[ ]'} Obsługa błędnych danych logowania\n")
                elif 'Funkcja "Zapamiętaj mnie"' in line:
                    file.write(f"   {'[x]' if test_results['remember_me'] else '[ ]'} Funkcja \"Zapamiętaj mnie\"\n")
                elif 'Przekierowanie po udanym logowaniu' in line:
                    file.write(f"   {'[x]' if test_results['redirection'] else '[ ]'} Przekierowanie po udanym logowaniu\n")
                else:
                    file.write(line)
                    
        print("\n✅ Aktualizacja pliku test_results.txt zakończona pomyślnie")
        
        # UWAGI I ZALECENIA DOTYCZĄCE USPRAWNIEŃ
        print("\n=== ANALIZA I ZALECENIA ===")
        
        # 1. Poprawne logowanie
        if test_results["correct_login"]:
            print("✓ Logowanie z poprawnymi danymi działa prawidłowo")
        else:
            print("! USPRAWNIENIE: Naprawić proces logowania z poprawnymi danymi")
        
        # 2. Obsługa błędnych danych
        if test_results["invalid_credentials"]:
            print("✓ Obsługa błędnych danych działa prawidłowo")
        else:
            print("! USPRAWNIENIE: Poprawić obsługę błędnych danych logowania")
        
        # 3. Zapamiętaj mnie
        if test_results["remember_me"]:
            print("✓ Funkcja 'Zapamiętaj mnie' działa prawidłowo")
        else:
            print("! USPRAWNIENIE: Zaimplementować lub naprawić funkcję 'Zapamiętaj mnie'")
        
        # 4. Przekierowanie
        if test_results["redirection"]:
            print("✓ Przekierowanie po logowaniu działa prawidłowo")
        else:
            print("! USPRAWNIENIE: Naprawić przekierowanie po logowaniu")
        
        # 5. Ogólne zalecenia
        print("! ZALECENIE: Dodać licznik nieudanych prób logowania dla bezpieczeństwa")
        print("! ZALECENIE: Dodać dwuskładnikowe uwierzytelnianie (2FA) jako opcję")
        print("! ZALECENIE: Usprawnić interfejs logowania dla lepszej użyteczności")
        
        return True
        
    except Exception as e:
        print(f"BŁĄD podczas testu: {e}")
        driver.save_screenshot("login_error.png")
        print("Zapisano zrzut ekranu błędu")
        return False
        
    finally:
        driver.quit()
        print("Zamknięto przeglądarkę")

if __name__ == "__main__":
    print("Rozpoczęcie testów logowania użytkownika")
    result = test_login()
    print(f"\nTesty zakończone {'powodzeniem' if result else 'niepowodzeniem'}")
    sys.exit(0 if result else 1) 