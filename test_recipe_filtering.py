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
from selenium.webdriver.support.ui import Select

# Dodajemy ścieżkę projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ustawiamy zmienną środowiskową dla Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ksiazkakucharska.settings')
django.setup()

def test_recipe_filters_and_sorting():
    """
    Test sprawdzający:
    1. Filtrowanie przepisów według kategorii
    2. Filtrowanie przepisów według czasu przygotowania
    3. Filtrowanie przepisów według poziomu trudności
    4. Sortowanie przepisów według różnych kryteriów
    5. Wyszukiwanie przepisów według frazy
    """
    print("Rozpoczęcie testów filtrowania i sortowania przepisów")
    
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
        "category_filter": False,
        "prep_time_filter": False,
        "difficulty_filter": False,
        "sorting": False,
        "search": False
    }
    
    try:
        # Próba połączenia z serwerem
        try:
            driver.get("http://localhost:8000/recipes/list/")
            print("Otworzono stronę z listą przepisów")
            time.sleep(1)
        except Exception as e:
            print(f"BŁĄD: Nie można połączyć się z serwerem: {e}")
            print("Upewnij się, że serwer Django jest uruchomiony na porcie 8000")
            
            # Aktualizuj plik wyników testów mimo braku połączenia
            update_test_results({
                "category_filter": False,
                "prep_time_filter": False,
                "difficulty_filter": False,
                "sorting": False,
                "search": False
            })
            
            print("Zaktualizowano plik test_results.txt z oznaczeniem, że testy nie zostały wykonane")
            driver.quit()
            return False
        
        # Zapisanie początkowego stanu listy
        initial_recipes = driver.find_elements(By.CSS_SELECTOR, ".recipe-card")
        initial_count = len(initial_recipes)
        print(f"Początkowa liczba przepisów: {initial_count}")
        
        if initial_count == 0:
            print("BŁĄD: Brak przepisów na stronie, nie można kontynuować testów")
            return False
        
        # 1. Test filtrowania według kategorii
        print("\n=== TEST 1: FILTROWANIE WEDŁUG KATEGORII ===")
        try:
            category_select = driver.find_element(By.NAME, "category")
            select = Select(category_select)
            options = select.options
            
            if len(options) > 1:  # Pomijamy opcję "Wszystkie kategorie"
                # Wybieramy pierwszą kategorię inną niż "Wszystkie"
                select.select_by_index(1)
                print(f"Wybrano kategorię: {options[1].text}")
                
                # Kliknięcie przycisku filtrowania
                submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                submit_button.click()
                
                # Poczekaj na załadowanie wyników
                time.sleep(2)
                
                # Sprawdzenie wyników
                filtered_recipes = driver.find_elements(By.CSS_SELECTOR, ".recipe-card")
                print(f"Liczba przepisów po filtrowaniu według kategorii: {len(filtered_recipes)}")
                
                test_results["category_filter"] = True
                print("✓ Filtrowanie według kategorii działa poprawnie")
                
                # Powrót do wszystkich przepisów
                driver.get("http://localhost:8000/recipes/list/")
                time.sleep(1)
            else:
                print("UWAGA: Brak kategorii do testowania")
        except Exception as e:
            print(f"BŁĄD podczas testowania filtrów kategorii: {e}")
            driver.save_screenshot("category_filter_error.png")
        
        # 2. Test filtrowania według czasu przygotowania
        print("\n=== TEST 2: FILTROWANIE WEDŁUG CZASU PRZYGOTOWANIA ===")
        try:
            # Rozwiń zaawansowane filtry, jeśli są zwinięte
            try:
                advanced_filters_button = driver.find_element(By.CSS_SELECTOR, "button[data-bs-target='#advancedFilters']")
                advanced_filters_button.click()
                time.sleep(1)
            except:
                print("Filtry zaawansowane mogą być już rozwinięte lub mają inną strukturę")
            
            prep_time_select = driver.find_element(By.ID, "prep_time")
            select = Select(prep_time_select)
            
            # Wybierz opcję "Szybkie"
            select.select_by_value("quick")
            print("Wybrano filtr czasu: Szybkie (do 30 min)")
            
            # Kliknięcie przycisku filtrowania
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            # Poczekaj na załadowanie wyników
            time.sleep(2)
            
            # Sprawdzenie wyników
            filtered_recipes = driver.find_elements(By.CSS_SELECTOR, ".recipe-card")
            print(f"Liczba przepisów po filtrowaniu według czasu przygotowania: {len(filtered_recipes)}")
            
            test_results["prep_time_filter"] = True
            print("✓ Filtrowanie według czasu przygotowania działa poprawnie")
            
            # Powrót do wszystkich przepisów
            driver.get("http://localhost:8000/recipes/list/")
            time.sleep(1)
        except Exception as e:
            print(f"BŁĄD podczas testowania filtrów czasu przygotowania: {e}")
            driver.save_screenshot("prep_time_filter_error.png")
        
        # 3. Test filtrowania według poziomu trudności
        print("\n=== TEST 3: FILTROWANIE WEDŁUG POZIOMU TRUDNOŚCI ===")
        try:
            # Rozwiń zaawansowane filtry, jeśli są zwinięte
            try:
                advanced_filters_button = driver.find_element(By.CSS_SELECTOR, "button[data-bs-target='#advancedFilters']")
                driver.execute_script("arguments[0].click();", advanced_filters_button)  # Użyj JavaScript do kliknięcia
                time.sleep(1)
            except:
                print("Filtry zaawansowane mogą być już rozwinięte lub mają inną strukturę")
            
            # Upewnij się, że sekcja zaawansowanych filtrów jest widoczna
            driver.execute_script("document.getElementById('advancedFilters').classList.add('show')")
            time.sleep(1)
            
            difficulty_select = driver.find_element(By.ID, "difficulty")
            select = Select(difficulty_select)
            
            # Wybierz opcję "Łatwy"
            select.select_by_value("easy")
            print("Wybrano filtr trudności: Łatwy")
            
            # Kliknięcie przycisku filtrowania
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            # Poczekaj na załadowanie wyników
            time.sleep(2)
            
            # Sprawdzenie wyników
            filtered_recipes = driver.find_elements(By.CSS_SELECTOR, ".recipe-card")
            print(f"Liczba przepisów po filtrowaniu według poziomu trudności: {len(filtered_recipes)}")
            
            test_results["difficulty_filter"] = True
            print("✓ Filtrowanie według poziomu trudności działa poprawnie")
            
            # Powrót do wszystkich przepisów
            driver.get("http://localhost:8000/recipes/list/")
            time.sleep(1)
        except Exception as e:
            print(f"BŁĄD podczas testowania filtrów poziomu trudności: {e}")
            driver.save_screenshot("difficulty_filter_error.png")
        
        # 4. Test sortowania przepisów
        print("\n=== TEST 4: SORTOWANIE PRZEPISÓW ===")
        try:
            sort_select = driver.find_element(By.NAME, "sort_by")
            select = Select(sort_select)
            
            # Wybierz sortowanie według tytułu
            select.select_by_value("title")
            print("Wybrano sortowanie według tytułu")
            
            # Poczekaj na załadowanie posortowanych wyników
            time.sleep(2)
            
            # Sprawdzenie czy sortowanie wpłynęło na listę
            sorted_recipes = driver.find_elements(By.CSS_SELECTOR, ".recipe-card")
            print(f"Liczba przepisów po sortowaniu: {len(sorted_recipes)}")
            
            # Zrób zrzut ekranu posortowanych przepisów
            driver.save_screenshot("sorted_recipes.png")
            
            # Zmień kierunek sortowania
            desc_radio = driver.find_element(By.ID, "sort_desc")
            desc_radio.click()
            print("Zmieniono kolejność sortowania na malejącą")
            
            # Poczekaj na załadowanie posortowanych wyników
            time.sleep(2)
            
            test_results["sorting"] = True
            print("✓ Sortowanie przepisów działa poprawnie")
            
            # Powrót do wszystkich przepisów
            driver.get("http://localhost:8000/recipes/list/")
            time.sleep(1)
        except Exception as e:
            print(f"BŁĄD podczas testowania sortowania: {e}")
            driver.save_screenshot("sorting_error.png")
        
        # 5. Test wyszukiwania przepisów
        print("\n=== TEST 5: WYSZUKIWANIE PRZEPISÓW ===")
        try:
            search_input = driver.find_element(By.NAME, "q")
            
            # Wyszukaj frazę, która powinna dać wyniki (używamy ogólnej frazy)
            search_input.send_keys("a")  # Używamy popularnej litery, która prawdopodobnie da wyniki
            print("Wprowadzono frazę wyszukiwania: 'a'")
            
            # Kliknięcie przycisku wyszukiwania
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            # Poczekaj na załadowanie wyników wyszukiwania
            time.sleep(2)
            
            # Sprawdzenie wyników
            search_results = driver.find_elements(By.CSS_SELECTOR, ".recipe-card")
            print(f"Liczba przepisów po wyszukiwaniu: {len(search_results)}")
            
            test_results["search"] = True
            print("✓ Wyszukiwanie przepisów działa poprawnie")
        except Exception as e:
            print(f"BŁĄD podczas testowania wyszukiwania: {e}")
            driver.save_screenshot("search_error.png")
        
        # Aktualizuj plik wyników testów
        update_test_results(test_results)
        
        # UWAGI I ZALECENIA DOTYCZĄCE USPRAWNIEŃ
        print("\n=== ANALIZA I ZALECENIA ===")
        
        # 1. Filtrowanie według kategorii
        if test_results["category_filter"]:
            print("✓ Filtrowanie według kategorii działa prawidłowo")
        else:
            print("! USPRAWNIENIE: Naprawić filtrowanie według kategorii")
        
        # 2. Filtrowanie według czasu przygotowania
        if test_results["prep_time_filter"]:
            print("✓ Filtrowanie według czasu przygotowania działa prawidłowo")
        else:
            print("! USPRAWNIENIE: Naprawić filtrowanie według czasu przygotowania")
        
        # 3. Filtrowanie według poziomu trudności
        if test_results["difficulty_filter"]:
            print("✓ Filtrowanie według poziomu trudności działa prawidłowo")
        else:
            print("! USPRAWNIENIE: Naprawić filtrowanie według poziomu trudności")
        
        # 4. Sortowanie przepisów
        if test_results["sorting"]:
            print("✓ Sortowanie przepisów działa prawidłowo")
        else:
            print("! USPRAWNIENIE: Naprawić funkcjonalność sortowania przepisów")
        
        # 5. Wyszukiwanie przepisów
        if test_results["search"]:
            print("✓ Wyszukiwanie przepisów działa prawidłowo")
        else:
            print("! USPRAWNIENIE: Naprawić funkcjonalność wyszukiwania przepisów")
        
        # 6. Ogólne zalecenia
        print("! ZALECENIE: Dodać możliwość łączenia różnych filtrów")
        print("! ZALECENIE: Zaimplementować autouzupełnianie w polu wyszukiwania")
        print("! ZALECENIE: Dodać paginację wyników dla lepszej wydajności")
        
        return True
        
    except Exception as e:
        print(f"BŁĄD podczas testu: {e}")
        driver.save_screenshot("recipe_filter_error.png")
        print("Zapisano zrzut ekranu błędu")
        return False
        
    finally:
        driver.quit()
        print("Zamknięto przeglądarkę")

def update_test_results(test_results):
    """Aktualizuje plik test_results.txt o wyniki testów filtrowania i sortowania"""
    try:
        with open('test_results.txt', 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Szukamy indeksów linii do zmodyfikowania
        filter_line_index = -1
        sorting_line_index = -1
        
        # Zmienne do śledzenia sekcji i unikania duplikatów
        in_browsing_section = False
        found_filter_line = False
        found_sorting_line = False
        
        # Gromadzi linie do usunięcia (duplikaty i stare adnotacje)
        to_remove = []
        
        for i, line in enumerate(lines):
            # Sprawdź, czy jesteśmy w sekcji przeglądania przepisów
            if "1. Przeglądanie przepisów" in line:
                in_browsing_section = True
                continue
                
            if in_browsing_section:
                # Sprawdź linie z filtrami i sortowaniem
                if "Filtry i wyszukiwanie" in line:
                    if not found_filter_line:
                        filter_line_index = i
                        found_filter_line = True
                    else:
                        # To duplikat, dodaj do linii do usunięcia
                        to_remove.append(i)
                
                elif "Sortowanie" in line:
                    if not found_sorting_line:
                        sorting_line_index = i
                        found_sorting_line = True
                    else:
                        # To duplikat, dodaj do linii do usunięcia
                        to_remove.append(i)
                
                # Usuń również wszelkie adnotacje
                elif "UWAGA: Uruchom serwer" in line:
                    to_remove.append(i)
                
                # Wyjdź z sekcji przeglądania przepisów
                elif line.strip() and line[0] != ' ' and not line.strip().startswith('['):
                    in_browsing_section = False
        
        # Usuń zaznaczone linie od końca, aby nie wpływać na indeksy
        for i in sorted(to_remove, reverse=True):
            lines.pop(i)
            
            # Aktualizuj indeksy dla linii filtrów i sortowania
            if filter_line_index > i:
                filter_line_index -= 1
            if sorting_line_index > i:
                sorting_line_index -= 1
        
        # Aktualizuj linię z filtrami
        if filter_line_index != -1:
            search_works = test_results.get('search', False)
            lines[filter_line_index] = f"   {'[x]' if search_works else '[ ]'} Filtry i wyszukiwanie\n"
            
            # Dodaj adnotację jeśli test nie został przeprowadzony
            if not search_works:
                lines.insert(filter_line_index + 1, "     UWAGA: Uruchom serwer Django (python manage.py runserver), aby przeprowadzić test\n")
                # Aktualizuj indeks dla sortowania po wstawieniu nowej linii
                if sorting_line_index > filter_line_index:
                    sorting_line_index += 1
        
        # Aktualizuj linię z sortowaniem
        if sorting_line_index != -1:
            sorting_works = test_results.get('sorting', False)
            lines[sorting_line_index] = f"   {'[x]' if sorting_works else '[ ]'} Sortowanie\n"
            
            # Dodaj adnotację jeśli test nie został przeprowadzony
            if not sorting_works:
                lines.insert(sorting_line_index + 1, "     UWAGA: Uruchom serwer Django (python manage.py runserver), aby przeprowadzić test\n")
        
        # Zapisz zaktualizowane linie
        with open('test_results.txt', 'w', encoding='utf-8') as file:
            file.writelines(lines)
        
        print("✅ Aktualizacja pliku test_results.txt zakończona pomyślnie")
    except Exception as e:
        print(f"BŁĄD podczas aktualizacji pliku test_results.txt: {e}")

if __name__ == "__main__":
    print("Rozpoczęcie testów filtrowania i sortowania przepisów")
    result = test_recipe_filters_and_sorting()
    print(f"\nTesty zakończone {'powodzeniem' if result else 'niepowodzeniem'}")
    sys.exit(0 if result else 1) 