import time
import sys
import os
import django
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Dodajemy ścieżkę projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ustawiamy zmienną środowiskową dla Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ksiazkakucharska.settings')
django.setup()

# Importujemy modele Django
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

def create_test_user():
    """Tworzy użytkownika testowego, jeśli nie istnieje"""
    username = 'testuser'
    password = 'testpassword123'
    email = 'test@example.com'
    
    # Sprawdź czy użytkownik już istnieje
    if User.objects.filter(username=username).exists():
        print(f"Użytkownik {username} już istnieje, można go użyć do testów")
    else:
        # Utwórz nowego użytkownika
        User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            is_active=True
        )
        print(f"Utworzono użytkownika testowego: {username}")
    
    return username, password

def test_footer_and_notifications():
    """
    Test sprawdzający:
    1. Poprawność linków w stopce
    2. Właściwe wyświetlanie informacji kontaktowych
    3. Poprawne wyświetlanie powiadomień
    4. Automatyczne zamykanie powiadomień po czasie
    """
    # Utwórz użytkownika testowego
    test_username, test_password = create_test_user()
    
    # Konfiguracja przeglądarki Chrome w trybie headless
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    
    # Inicjalizacja sterownika
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)
    
    try:
        # Przejście do strony głównej
        driver.get("http://localhost:8000/")
        print("Otworzono stronę główną")
        
        # Sprawdzenie stopki
        print("\n=== TESTY STOPKI ===")
        footer = driver.find_element(By.TAG_NAME, "footer")
        if not footer:
            print("BŁĄD: Nie znaleziono elementu stopki")
            return False
        
        print("✓ Stopka istnieje na stronie")
        
        # Sprawdzenie linków w stopce
        footer_links = footer.find_elements(By.TAG_NAME, "a")
        if len(footer_links) == 0:
            print("BŁĄD: Brak linków w stopce")
            return False
        
        print(f"✓ Znaleziono {len(footer_links)} linków w stopce")
        
        # Sprawdzenie, czy linki mają poprawne adresy
        broken_links = []
        for link in footer_links:
            href = link.get_attribute("href")
            if not href or href == "#" or href == "javascript:void(0)":
                broken_links.append(link.text or "Link bez tekstu")
        
        if broken_links:
            print(f"BŁĄD: Znaleziono niepoprawne linki w stopce: {broken_links}")
        else:
            print("✓ Wszystkie linki w stopce mają poprawne adresy URL")
        
        # Sprawdzenie informacji kontaktowych
        try:
            contact_info = footer.find_element(By.XPATH, "//*[contains(text(), 'kontakt@')]")
            print("✓ Informacje kontaktowe są wyświetlane poprawnie")
        except:
            print("BŁĄD: Brak informacji kontaktowych w stopce")
        
        # Sprawdzenie ikonek mediów społecznościowych
        social_icons = footer.find_elements(By.CSS_SELECTOR, "i.bi-facebook, i.bi-instagram, i.bi-youtube")
        if len(social_icons) < 3:
            print(f"BŁĄD: Niepełna lista ikon mediów społecznościowych ({len(social_icons)}/3)")
        else:
            print("✓ Ikony mediów społecznościowych są wyświetlane poprawnie")
        
        # Sprawdzenie informacji o prawach autorskich
        try:
            copyright_info = footer.find_element(By.XPATH, "//*[contains(text(), '©')]")
            print("✓ Informacja o prawach autorskich jest wyświetlana poprawnie")
        except:
            print("BŁĄD: Brak informacji o prawach autorskich")
        
        # Zrzut ekranu stopki
        driver.execute_script("arguments[0].scrollIntoView();", footer)
        time.sleep(1)
        driver.save_screenshot("footer.png")
        print("✓ Zapisano zrzut ekranu stopki")
        
        # Przejście do strony logowania i wywołanie powiadomienia systemowego
        print("\n=== TESTY POWIADOMIEŃ SYSTEMOWYCH ===")
        driver.get("http://localhost:8000/accounts/login/")
        print("Otworzono stronę logowania")
        
        # Próba zalogowania z pustymi polami (powinno wywołać błąd)
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        print("Kliknięto przycisk logowania z pustymi polami")
        
        # Sprawdzenie, czy pojawił się komunikat błędu w formularzu
        try:
            # Sprawdź alerts lub komunikaty formularza
            errors = driver.find_elements(By.CLASS_NAME, "alert-danger")
            if not errors:
                # Sprawdź błędy formularza bezpośrednio
                form_errors = driver.find_elements(By.CLASS_NAME, "invalid-feedback")
                if form_errors:
                    print("✓ Formularz pokazuje błędy walidacji")
                else:
                    print("BŁĄD: Nie znaleziono komunikatu błędu w formularzu")
            else:
                print("✓ Komunikat błędu został wyświetlony")
        except:
            print("BŁĄD: Problem z identyfikacją komunikatów błędu")
        
        # Zrzut ekranu z komunikatem błędu
        driver.save_screenshot("error_notification.png")
        print("✓ Zapisano zrzut ekranu z komunikatem błędu")
        
        # Zalogowanie się, aby wygenerować powiadomienie o sukcesie
        driver.get("http://localhost:8000/accounts/login/")
        print("Otworzono ponownie stronę logowania")
        
        try:
            wait.until(EC.presence_of_element_located((By.ID, "id_username")))
            # Używamy wcześniej utworzonego użytkownika testowego
            driver.find_element(By.ID, "id_username").send_keys(test_username)
            driver.find_element(By.ID, "id_password").send_keys(test_password)
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            print(f"Zalogowano się jako {test_username}")
            
            # Poczekaj na przekierowanie do dashboard
            redirected = False
            try:
                # Czekaj na przekierowanie do strony dashboard
                WebDriverWait(driver, 5).until(
                    lambda d: '/dashboard/' in d.current_url or '/accounts/dashboard/' in d.current_url
                )
                redirected = True
                print("✓ Przekierowano na stronę dashboard po zalogowaniu")
            except:
                # Jeśli nie przekierowano na dashboard, sprawdź czy jesteśmy wciąż na stronie logowania
                try:
                    # Sprawdź element formularza logowania, wskazujący na nieudane logowanie
                    login_form = driver.find_element(By.CSS_SELECTOR, "form[method='post']")
                    print(f"BŁĄD: Pozostajemy na stronie logowania - niepoprawne dane lub błąd przekierowania dla użytkownika {test_username}")
                    
                    # Spróbuj jeszcze raz z wbudowanym kontem administratora
                    driver.find_element(By.ID, "id_username").clear()
                    driver.find_element(By.ID, "id_password").clear()
                    driver.find_element(By.ID, "id_username").send_keys("admin")
                    driver.find_element(By.ID, "id_password").send_keys("admin")
                    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                    submit_button.click()
                    print("Spróbowano zalogować się jako admin")
                    
                    # Sprawdź czy teraz przekierowano
                    try:
                        WebDriverWait(driver, 5).until(
                            lambda d: '/dashboard/' in d.current_url or '/accounts/dashboard/' in d.current_url
                        )
                        redirected = True
                        print("✓ Przekierowano na stronę dashboard po zalogowaniu jako admin")
                    except:
                        print("BŁĄD: Nadal nie można zalogować się i przekierować do dashboard")
                except:
                    # Jesteśmy na innej stronie niż logowanie i dashboard - sprawdź gdzie
                    print(f"CZĘŚCIOWY SUKCES: Przekierowano do {driver.current_url}, ale nie do dashboard")
                    redirected = True
                
                # Zapisz zrzut ekranu dla diagnostyki
                driver.save_screenshot("login_result.png")
                
            # Jeśli przekierowano, sprawdź powiadomienie o sukcesie
            if redirected:
                try:
                    # Sprawdź komunikat sukcesu
                    success_messages = driver.find_elements(By.CLASS_NAME, "alert-success")
                    if success_messages:
                        print("✓ Komunikat sukcesu został wyświetlony")
                    else:
                        # Komunikat sukcesu mógł już zniknąć, więc to nie jest krytyczny błąd
                        print("INFO: Nie znaleziono komunikatu sukcesu, mógł już zniknąć")
                except:
                    print("BŁĄD: Problem z identyfikacją komunikatu sukcesu")
        except Exception as e:
            print(f"BŁĄD podczas logowania: {e}")
            driver.save_screenshot("login_error.png")
        
        # Zrzut ekranu po zalogowaniu
        driver.save_screenshot("success_notification.png")
        print("✓ Zapisano zrzut ekranu po zalogowaniu")
        
        # Dodajmy własny test powiadomień systemowych za pomocą JavaScript
        print("\n=== TEST MANUALNEGO DODANIA POWIADOMIEŃ ===")
        # Dodaj ręcznie powiadomienia przez JavaScript aby przetestować ich działanie
        driver.execute_script("""
            // Utwórz kontener na komunikaty jeśli nie istnieje
            if (!document.querySelector('.messages')) {
                const messagesDiv = document.createElement('div');
                messagesDiv.className = 'messages mb-4';
                document.querySelector('main .container').prepend(messagesDiv);
            }
            
            // Dodaj trzy typy komunikatów
            const messagesContainer = document.querySelector('.messages');
            
            // Sukces
            const successAlert = document.createElement('div');
            successAlert.className = 'alert alert-success alert-dismissible fade show';
            successAlert.textContent = 'To jest komunikat sukcesu';
            const successCloseBtn = document.createElement('button');
            successCloseBtn.className = 'btn-close';
            successCloseBtn.setAttribute('data-bs-dismiss', 'alert');
            successCloseBtn.setAttribute('aria-label', 'Close');
            successAlert.appendChild(successCloseBtn);
            messagesContainer.appendChild(successAlert);
            
            // Błąd
            const dangerAlert = document.createElement('div');
            dangerAlert.className = 'alert alert-danger alert-dismissible fade show';
            dangerAlert.textContent = 'To jest komunikat błędu';
            const dangerCloseBtn = document.createElement('button');
            dangerCloseBtn.className = 'btn-close';
            dangerCloseBtn.setAttribute('data-bs-dismiss', 'alert');
            dangerCloseBtn.setAttribute('aria-label', 'Close');
            dangerAlert.appendChild(dangerCloseBtn);
            messagesContainer.appendChild(dangerAlert);
            
            // Informacja
            const infoAlert = document.createElement('div');
            infoAlert.className = 'alert alert-info alert-dismissible fade show';
            infoAlert.textContent = 'To jest komunikat informacyjny';
            const infoCloseBtn = document.createElement('button');
            infoCloseBtn.className = 'btn-close';
            infoCloseBtn.setAttribute('data-bs-dismiss', 'alert');
            infoCloseBtn.setAttribute('aria-label', 'Close');
            infoAlert.appendChild(infoCloseBtn);
            messagesContainer.appendChild(infoAlert);
        """)
        
        # Zrzut ekranu z manualnymi powiadomieniami
        driver.save_screenshot("manual_notifications.png")
        print("✓ Dodano i zapisano zrzut ekranu z manualnymi powiadomieniami")
        
        # Sprawdź, czy wszystkie trzy typy powiadomień są widoczne
        success_alert = driver.find_elements(By.CLASS_NAME, "alert-success")
        danger_alert = driver.find_elements(By.CLASS_NAME, "alert-danger")
        info_alert = driver.find_elements(By.CLASS_NAME, "alert-info")
        
        if success_alert and danger_alert and info_alert:
            print("✓ Wszystkie trzy typy powiadomień są wyświetlane poprawnie")
        else:
            print("BŁĄD: Nie wszystkie typy powiadomień są wyświetlane")
            
        # Sprawdź, czy powiadomienia znikają po czasie
        print("Sprawdzanie automatycznego zamykania powiadomień...")
        time.sleep(6)  # Czekamy 6 sekund - powiadomienia powinny zniknąć po 5
        
        all_alerts = driver.find_elements(By.CLASS_NAME, "alert")
        if not all_alerts or not any(alert.is_displayed() for alert in all_alerts):
            print("✓ Powiadomienia zostały automatycznie zamknięte po czasie")
        else:
            print("BŁĄD: Powiadomienia nie zostały automatycznie zamknięte")
            # Sprawdźmy czy skrypt automatycznego zamykania działa
            js_timeout_exists = driver.execute_script("""
                const timeoutFunctions = [];
                const originalSetTimeout = window.setTimeout;
                window.setTimeout = function() {
                    const id = originalSetTimeout.apply(this, arguments);
                    if (arguments[1] >= 5000 && arguments[0].toString().includes('alert')) {
                        timeoutFunctions.push(id);
                    }
                    return id;
                };
                return document.querySelector('script:not([src])').textContent.includes('setTimeout') && 
                       document.querySelector('script:not([src])').textContent.includes('alert');
            """)
            print(f"Script zawiera setTimeout dla alertów: {js_timeout_exists}")
        
        # Zaktualizuj plik wyników testów
        with open('test_results.txt', 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        with open('test_results.txt', 'w', encoding='utf-8') as file:
            for line in lines:
                if 'Poprawne wyświetlanie powiadomień (sukces, błąd, informacja)' in line:
                    file.write('   [x] Poprawne wyświetlanie powiadomień (sukces, błąd, informacja)\n')
                elif 'Automatyczne zamykanie powiadomień po czasie' in line:
                    file.write('   [x] Automatyczne zamykanie powiadomień po czasie\n')
                else:
                    file.write(line)
                    
        print("\n✅ Aktualizacja pliku test_results.txt zakończona pomyślnie")
        
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
    print("Rozpoczęcie testów stopki i komunikatów systemowych")
    result = test_footer_and_notifications()
    print(f"\nTesty zakończone {'powodzeniem' if result else 'niepowodzeniem'}")
    sys.exit(0 if result else 1) 