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
from django.core import mail

def generate_random_username():
    """Generuje losową nazwę użytkownika na potrzeby testów"""
    return 'testuser_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def generate_random_email():
    """Generuje losowy adres email na potrzeby testów"""
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{username}@example.com"

def test_registration():
    """
    Test sprawdzający:
    1. Poprawną rejestrację z poprawnymi danymi
    2. Walidację pól formularza
    3. Obsługę błędów (np. zajęty login/email)
    4. Przekierowanie po udanej rejestracji
    """
    print("Rozpoczęcie testów rejestracji")
    
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
        "correct_registration": False,
        "form_validation": False,
        "duplicate_username": False,
        "duplicate_email": False,
        "redirection": False
    }
    
    try:
        # Przejście do strony rejestracji
        driver.get("http://localhost:8000/accounts/register/")
        print("Otworzono stronę rejestracji")
        
        # 1. Test poprawnej rejestracji z poprawnymi danymi
        print("\n=== TEST 1: POPRAWNA REJESTRACJA ===")
        
        # Generowanie losowej nazwy użytkownika i emaila
        username = generate_random_username()
        email = generate_random_email()
        password = "TestPassword123"
        
        # Wypełnienie formularza poprawnymi danymi
        wait.until(EC.presence_of_element_located((By.ID, "id_username")))
        driver.find_element(By.ID, "id_username").send_keys(username)
        driver.find_element(By.ID, "id_email").send_keys(email)
        driver.find_element(By.ID, "id_first_name").send_keys("Test")
        driver.find_element(By.ID, "id_last_name").send_keys("User")
        driver.find_element(By.ID, "id_password1").send_keys(password)
        driver.find_element(By.ID, "id_password2").send_keys(password)
        
        # Przewinięcie do checkboxa regulaminu
        checkbox = driver.find_element(By.ID, "termsCheck")
        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
        time.sleep(1)  # Dajemy czas na przewinięcie
        
        # Zaznaczenie checkboxa za pomocą JavaScript
        driver.execute_script("arguments[0].click();", checkbox)
        
        # Kliknięcie przycisku rejestracji za pomocą JavaScript
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", submit_button)
        
        # Sprawdzenie przekierowania do strony potwierdzenia
        try:
            WebDriverWait(driver, 5).until(
                lambda d: '/activation-sent/' in d.current_url or '/accounts/activation-sent/' in d.current_url
            )
            print("✓ Przekierowano na stronę potwierdzenia wysłania emaila aktywacyjnego")
            test_results["redirection"] = True
            
            # Sprawdzenie treści strony
            try:
                activation_sent_text = driver.find_element(By.CSS_SELECTOR, ".alert-success").text
                if "wysłaliśmy link aktywacyjny" in activation_sent_text:
                    print("✓ Strona zawiera informację o wysłaniu linku aktywacyjnego")
                else:
                    print("BŁĄD: Strona nie zawiera informacji o wysłaniu linku aktywacyjnego")
            except:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                if "wysłaliśmy link aktywacyjny" in body_text:
                    print("✓ Strona zawiera informację o wysłaniu linku aktywacyjnego (znaleziono w treści strony)")
                else:
                    print("BŁĄD: Strona nie zawiera informacji o wysłaniu linku aktywacyjnego")
            
            # Sprawdzenie, czy użytkownik został utworzony w bazie
            try:
                user = User.objects.get(username=username)
                if user and not user.is_active:
                    print(f"✓ Użytkownik {username} został utworzony jako nieaktywny")
                    test_results["correct_registration"] = True
                else:
                    print(f"UWAGA: Użytkownik {username} jest aktywny bez aktywacji")
            except User.DoesNotExist:
                print(f"BŁĄD: Użytkownik {username} nie został utworzony w bazie danych")
            
            # Próba sprawdzenia wiadomości email
            try:
                # W środowisku testowym, jeśli mail.outbox jest dostępny, sprawdź jego zawartość
                if hasattr(mail, 'outbox') and len(mail.outbox) > 0:
                    last_email = mail.outbox[-1]
                    if username in last_email.body and "Aktywacja konta" in last_email.subject:
                        print(f"✓ Email aktywacyjny został wysłany do {email}")
                    else:
                        print("BŁĄD: Wysłany email nie zawiera informacji o aktywacji konta")
                else:
                    print("UWAGA: Nie można sprawdzić wysłanych emaili w tym środowisku")
            except:
                print("UWAGA: Nie udało się sprawdzić wysłanych emaili")
                
        except TimeoutException:
            print("BŁĄD: Nie przekierowano na stronę potwierdzenia")
            driver.save_screenshot("registration_failed.png")
            print("Zapisano zrzut ekranu problemu rejestracji")
        
        # 2. Test walidacji pól formularza
        print("\n=== TEST 2: WALIDACJA PÓL FORMULARZA ===")
        
        # Przejście ponownie do strony rejestracji
        driver.get("http://localhost:8000/accounts/register/")
        print("Otworzono stronę rejestracji ponownie")
        
        # Próba wysłania pustego formularza
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit']")))
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", submit_button)
        
        # Sprawdzenie, czy pojawiły się komunikaty błędów
        time.sleep(1)  # Dajemy czas na przetworzenie formularza
        page_source = driver.page_source
        
        if "To pole jest wymagane" in page_source or "alert-danger" in page_source:
            print("✓ Wyświetlono komunikaty o błędach dla pustego formularza")
            
            # Sprawdzenie, czy formularz nie został wysłany
            if "activation-sent" not in driver.current_url:
                print("✓ Formularz nie został wysłany z błędnymi danymi")
                test_results["form_validation"] = True
            else:
                print("BŁĄD: Formularz został wysłany mimo błędnych danych")
        else:
            print("BŁĄD: Nie wyświetlono komunikatów o błędach dla pustego formularza")
            driver.save_screenshot("validation_failed.png")
            print("Zapisano zrzut ekranu problemu walidacji")
        
        # 3. Test obsługi istniejącej nazwy użytkownika
        print("\n=== TEST 3: OBSŁUGA ISTNIEJĄCEJ NAZWY UŻYTKOWNIKA ===")
        
        # Tylko jeśli rejestracja się powiodła i użytkownik został utworzony
        if test_results["correct_registration"]:
            # Przejście ponownie do strony rejestracji
            driver.get("http://localhost:8000/accounts/register/")
            print("Otworzono stronę rejestracji ponownie")
            
            # Wypełnienie formularza z istniejącą nazwą użytkownika
            wait.until(EC.presence_of_element_located((By.ID, "id_username")))
            driver.find_element(By.ID, "id_username").send_keys(username)  # Taka sama nazwa jak wcześniej
            driver.find_element(By.ID, "id_email").send_keys(generate_random_email())  # Nowy email
            driver.find_element(By.ID, "id_password1").send_keys(password)
            driver.find_element(By.ID, "id_password2").send_keys(password)
            
            # Zaznaczenie checkboxa za pomocą JavaScript
            checkbox = driver.find_element(By.ID, "termsCheck")
            driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", checkbox)
            
            # Kliknięcie przycisku rejestracji
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            driver.execute_script("arguments[0].click();", submit_button)
            
            # Sprawdzenie, czy pojawił się komunikat o istniejącej nazwie użytkownika
            time.sleep(2)  # Krótkie oczekiwanie na przetworzenie formularza
            page_content = driver.page_source
            
            if "Użytkownik o tej nazwie już istnieje" in page_content or "already exists" in page_content:
                print("✓ Wyświetlono komunikat o istniejącej nazwie użytkownika")
                
                # Sprawdzenie, czy formularz nie został wysłany
                if "activation-sent" not in driver.current_url:
                    print("✓ Formularz nie został wysłany z istniejącą nazwą użytkownika")
                    test_results["duplicate_username"] = True
                else:
                    print("BŁĄD: Formularz został wysłany mimo istniejącej nazwy użytkownika")
            else:
                print("BŁĄD: Nie wyświetlono komunikatu o istniejącej nazwie użytkownika")
                driver.save_screenshot("duplicate_username_failed.png")
                print("Zapisano zrzut ekranu problemu z duplikatem nazwy")
        else:
            print("POMINIĘTO: Test duplikatu nazwy użytkownika (brak zarejestrowanego użytkownika)")
            
        # 4. Test obsługi istniejącego adresu email
        print("\n=== TEST 4: OBSŁUGA ISTNIEJĄCEGO ADRESU EMAIL ===")
        
        # Tylko jeśli rejestracja się powiodła i użytkownik został utworzony
        if test_results["correct_registration"]:
            # Przejście ponownie do strony rejestracji
            driver.get("http://localhost:8000/accounts/register/")
            print("Otworzono stronę rejestracji ponownie")
            
            # Wypełnienie formularza z istniejącym adresem email
            wait.until(EC.presence_of_element_located((By.ID, "id_username")))
            driver.find_element(By.ID, "id_username").send_keys(generate_random_username())  # Nowa nazwa
            driver.find_element(By.ID, "id_email").send_keys(email)  # Ten sam email
            driver.find_element(By.ID, "id_password1").send_keys(password)
            driver.find_element(By.ID, "id_password2").send_keys(password)
            
            # Zaznaczenie checkboxa za pomocą JavaScript
            checkbox = driver.find_element(By.ID, "termsCheck")
            driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", checkbox)
            
            # Kliknięcie przycisku rejestracji
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            driver.execute_script("arguments[0].click();", submit_button)
            
            # Sprawdzenie, czy pojawił się komunikat o istniejącym adresie email
            time.sleep(2)  # Krótkie oczekiwanie na przetworzenie formularza
            page_content = driver.page_source
            
            if "Użytkownik z tym adresem email już istnieje" in page_content or "email already exists" in page_content:
                print("✓ Wyświetlono komunikat o istniejącym adresie email")
                
                # Sprawdzenie, czy formularz nie został wysłany
                if "activation-sent" not in driver.current_url:
                    print("✓ Formularz nie został wysłany z istniejącym adresem email")
                    test_results["duplicate_email"] = True
                else:
                    print("BŁĄD: Formularz został wysłany mimo istniejącego adresu email")
            else:
                print("BŁĄD: Nie wyświetlono komunikatu o istniejącym adresie email")
                driver.save_screenshot("duplicate_email_failed.png")
                print("Zapisano zrzut ekranu problemu z duplikatem emaila")
        else:
            print("POMINIĘTO: Test duplikatu emaila (brak zarejestrowanego użytkownika)")
        
        # Zaktualizuj plik wyników testów
        with open('test_results.txt', 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        with open('test_results.txt', 'w', encoding='utf-8') as file:
            for line in lines:
                if 'Poprawna rejestracja z poprawnymi danymi' in line:
                    file.write(f"   {'[x]' if test_results['correct_registration'] else '[ ]'} Poprawna rejestracja z poprawnymi danymi\n")
                elif 'Walidacja pól formularza' in line:
                    file.write(f"   {'[x]' if test_results['form_validation'] else '[ ]'} Walidacja pól formularza\n")
                elif 'Obsługa błędów (np. zajęty login/email)' in line:
                    if test_results['duplicate_username'] and test_results['duplicate_email']:
                        file.write("   [x] Obsługa błędów (np. zajęty login/email)\n")
                    else:
                        file.write("   [ ] Obsługa błędów (np. zajęty login/email)\n")
                elif 'Przekierowanie po udanej rejestracji' in line:
                    file.write(f"   {'[x]' if test_results['redirection'] else '[ ]'} Przekierowanie po udanej rejestracji\n")
                else:
                    file.write(line)
                    
        print("\n✅ Aktualizacja pliku test_results.txt zakończona pomyślnie")
        
        # UWAGI I ZALECENIA DOTYCZĄCE USPRAWNIEŃ
        print("\n=== ANALIZA I ZALECENIA ===")
        
        # 1. Sprawdzenie wzorców walidacji formularza
        if test_results["form_validation"]:
            print("✓ Walidacja formularza działa prawidłowo")
        else:
            print("! USPRAWNIENIE: Należy poprawić walidację formularza, szczególnie w zakresie wyświetlania komunikatów o błędach")
        
        # 2. Sprawdzenie przekierowania po rejestracji
        if test_results["redirection"]:
            print("✓ Przekierowanie po rejestracji działa prawidłowo")
        else:
            print("! USPRAWNIENIE: Poprawić mechanizm przekierowania po rejestracji")
        
        # 3. Sprawdzenie obsługi duplikatów
        if test_results["duplicate_username"] and test_results["duplicate_email"]:
            print("✓ Obsługa duplikatów działa prawidłowo")
        else:
            print("! USPRAWNIENIE: Poprawić obsługę duplikatów nazwy użytkownika i adresu email")
        
        # 4. Ogólne zalecenia
        print("! ZALECENIE: Dodać walidację JavaScript po stronie klienta dla szybszej informacji zwrotnej")
        print("! ZALECENIE: Ulepszyć style komunikatów o błędach dla lepszej widoczności")
        print("! ZALECENIE: Dodać wskaźnik siły hasła dla lepszego UX")
        
        return True
        
    except Exception as e:
        print(f"BŁĄD podczas testu: {e}")
        driver.save_screenshot("registration_error.png")
        print("Zapisano zrzut ekranu błędu")
        return False
        
    finally:
        driver.quit()
        print("Zamknięto przeglądarkę")

if __name__ == "__main__":
    print("Rozpoczęcie testów rejestracji użytkownika")
    result = test_registration()
    print(f"\nTesty zakończone {'powodzeniem' if result else 'niepowodzeniem'}")
    sys.exit(0 if result else 1) 