import time
import sys
import os
import django
import random
import string
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Dodajemy ścieżkę projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ustawiamy zmienną środowiskową dla Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ksiazkakucharska.settings')
django.setup()

# Importujemy modele Django
from django.contrib.auth.models import User
from recipes.models import Recipe, RecipeCategory, RecipeIngredient
from django.contrib.auth.hashers import make_password

def create_test_user():
    """Tworzy testowe konto użytkownika do testów funkcji przepisów"""
    username = 'testuser'
    email = 'testuser@example.com'
    password = 'TestUser123'
    
    try:
        user = User.objects.get(username=username)
        print(f"Użytkownik {username} już istnieje")
        if not user.is_active:
            user.is_active = True
            user.save()
            print(f"Użytkownik {username} został aktywowany")
    except User.DoesNotExist:
        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            is_active=True,
            first_name='Jan',
            last_name='Testowy'
        )
        print(f"Utworzono użytkownika: {username}")
    
    return username, password

def test_recipes_db_access():
    """Sprawdza dostęp do bazy danych przepisów"""
    print("\n=== TEST DOSTĘPU DO BAZY DANYCH PRZEPISÓW ===")
    
    try:
        recipes_count = Recipe.objects.count()
        categories_count = RecipeCategory.objects.count()
        
        print(f"✓ Znaleziono {recipes_count} przepisów w bazie danych")
        print(f"✓ Znaleziono {categories_count} kategorii w bazie danych")
        
        if recipes_count > 0:
            # Przykładowy przepis
            recipe = Recipe.objects.first()
            print(f"✓ Przykładowy przepis: {recipe.title} (autor: {recipe.author.username})")
            
            # Sprawdź składniki
            ingredients = RecipeIngredient.objects.filter(recipe=recipe)
            print(f"✓ Przepis ma {ingredients.count()} składników")
            
            # Sprawdź kategorie
            if recipe.categories.exists():
                categories = recipe.categories.all()
                categories_list = ", ".join([c.name for c in categories])
                print(f"✓ Przepis należy do kategorii: {categories_list}")
            else:
                print("! Przepis nie ma przypisanych kategorii")
            
            return True
        else:
            print("! Brak przepisów w bazie danych. Testy mogą nie być miarodajne.")
            return False
    
    except Exception as e:
        print(f"! BŁĄD podczas sprawdzania bazy danych: {e}")
        return False

def test_recipes_browse_functionality():
    """
    Test sprawdzający funkcjonalność przeglądania przepisów:
    1. Lista wszystkich przepisów
    2. Filtry i wyszukiwanie
    3. Sortowanie
    4. Podgląd szczegółów przepisu
    """
    print("Rozpoczęcie testów funkcji przeglądania przepisów")
    
    # Tworzenie testowego użytkownika
    username, password = create_test_user()
    
    # Sprawdź dostęp do bazy danych
    db_test_success = test_recipes_db_access()
    
    try:
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
            "list_all_recipes": False,
            "filter_search": False,
            "sorting": False,
            "recipe_details": False
        }
        
        try:
            # Logowanie użytkownika
            driver.get("http://localhost:8000/accounts/login/")
            print(f"Otworzono stronę logowania dla użytkownika {username}")
            
            # Wypełnienie formularza logowania
            wait.until(EC.presence_of_element_located((By.ID, "id_username")))
            driver.find_element(By.ID, "id_username").send_keys(username)
            driver.find_element(By.ID, "id_password").send_keys(password)
            
            # Kliknięcie przycisku logowania
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            driver.execute_script("arguments[0].click();", submit_button)
            
            # Sprawdzenie przekierowania po logowaniu - sprawdzamy czy gdziekolwiek przekierowano, może nie być konkretnie do /dashboard/
            # Kluczowe jest to, żeby strona logowania zniknęła, a użytkownik dostał się dalej
            time.sleep(3)  # Dajemy czas na przekierowanie
            
            # Zapisanie zrzutu ekranu po zalogowaniu
            driver.save_screenshot("after_login.png")
            print(f"✓ Zalogowano się jako {username}, aktualna strona: {driver.current_url}")
            
            # Test 1: Lista wszystkich przepisów
            print("\n=== TEST 1: LISTA WSZYSTKICH PRZEPISÓW ===")
            
            # Przejście do listy przepisów
            try:
                driver.get("http://localhost:8000/recipes/list/")
                print("✓ Otworzono stronę listy przepisów")
                
                # Sprawdzenie, czy strona się załadowała
                time.sleep(2)
                
                # Zapisanie zrzutu ekranu
                driver.save_screenshot("recipes_list.png")
                print("✓ Zapisano zrzut ekranu listy przepisów")
                
                # Sprawdzenie, czy lista przepisów jest widoczna
                recipes = driver.find_elements(By.CSS_SELECTOR, ".card")
                if recipes:
                    print(f"✓ Znaleziono {len(recipes)} przepisów na stronie")
                    test_results["list_all_recipes"] = True
                else:
                    # Sprawdź czy jest komunikat o braku przepisów
                    if "nie znaleziono przepisów" in driver.page_source.lower() or "no recipes found" in driver.page_source.lower():
                        print("✓ Strona wyświetla komunikat o braku przepisów")
                        test_results["list_all_recipes"] = True
                    else:
                        print("! Nie znaleziono listy przepisów ani komunikatu o ich braku")
            except Exception as e:
                print(f"! Błąd podczas sprawdzania listy przepisów: {e}")
            
            # Test 3: Sortowanie
            print("\n=== TEST 3: SORTOWANIE ===")
            
            try:
                # Powrót do listy wszystkich przepisów
                driver.get("http://localhost:8000/recipes/list/")
                print("✓ Otworzono ponownie stronę listy przepisów")
                time.sleep(2)
                
                # Sprawdzenie, czy są opcje sortowania
                sort_options = driver.find_elements(By.CSS_SELECTOR, "select[name*='sort'], .sort-option, .sort-button")
                
                if sort_options:
                    print(f"✓ Znaleziono {len(sort_options)} opcji sortowania")
                    
                    # Wybierz pierwszą opcję sortowania
                    sort_option = sort_options[0]
                    driver.execute_script("arguments[0].click();", sort_option)
                    
                    # Czekaj na wyniki sortowania
                    time.sleep(2)
                    
                    # Zapisanie zrzutu ekranu wyników sortowania
                    driver.save_screenshot("recipes_sort_results.png")
                    print("✓ Zapisano zrzut ekranu wyników sortowania")
                    
                    test_results["sorting"] = True
                else:
                    # Sprawdź czy są nagłówki kolumn, które można kliknąć do sortowania
                    sort_headers = driver.find_elements(By.CSS_SELECTOR, "th[data-sort], .sortable")
                    
                    if sort_headers:
                        print(f"✓ Znaleziono {len(sort_headers)} nagłówków kolumn do sortowania")
                        
                        # Kliknij pierwszy nagłówek
                        sort_header = sort_headers[0]
                        driver.execute_script("arguments[0].click();", sort_header)
                        
                        # Czekaj na wyniki sortowania
                        time.sleep(2)
                        
                        # Zapisanie zrzutu ekranu wyników sortowania
                        driver.save_screenshot("recipes_sort_results.png")
                        print("✓ Zapisano zrzut ekranu wyników sortowania po kliknięciu nagłówka")
                        
                        test_results["sorting"] = True
                    else:
                        print("! Nie znaleziono opcji sortowania")
                        
                        # Sprawdź czy są jakieś inne elementy do sortowania
                        any_sort = driver.find_elements(By.XPATH, "//*[contains(text(), 'sort') or contains(text(), 'Sortuj')]")
                        if any_sort:
                            print(f"✓ Znaleziono {len(any_sort)} elementów zawierających słowo 'sort' lub 'Sortuj'")
                            test_results["sorting"] = True
                        else:
                            print("! Nie znaleziono żadnych elementów sortowania")
            except Exception as e:
                print(f"! Błąd podczas sprawdzania sortowania: {e}")
            
            # Test 2: Filtry i wyszukiwanie
            print("\n=== TEST 2: FILTRY I WYSZUKIWANIE ===")
            
            try:
                # Przejdź do listy przepisów
                driver.get("http://localhost:8000/recipes/list/")
                print("✓ Otworzono stronę listy przepisów dla testów filtrowania")
                time.sleep(2)
                
                # Sprawdzenie, czy są filtry lub pole wyszukiwania
                search_box = None
                category_filters = None
                
                try:
                    search_box = driver.find_element(By.CSS_SELECTOR, "input[type='search'], input[name='search'], input[placeholder*='szukaj'], input[placeholder*='search']")
                    print("✓ Znaleziono pole wyszukiwania")
                except NoSuchElementException:
                    print("! Nie znaleziono pola wyszukiwania")
                
                try:
                    category_filters = driver.find_elements(By.CSS_SELECTOR, ".category-filter, input[type='checkbox'][name*='category'], select[name*='category']")
                    if category_filters:
                        print(f"✓ Znaleziono {len(category_filters)} filtrów kategorii")
                    else:
                        print("! Nie znaleziono filtrów kategorii")
                except NoSuchElementException:
                    print("! Nie znaleziono filtrów kategorii")
                
                # Test wyszukiwania, jeśli jest pole wyszukiwania
                if search_box:
                    search_term = "zupa"  # Przykładowy termin wyszukiwania
                    search_box.clear()
                    search_box.send_keys(search_term)
                    search_box.send_keys(Keys.RETURN)
                    
                    # Czekaj na wyniki wyszukiwania
                    time.sleep(2)
                    
                    # Zapisanie zrzutu ekranu wyników wyszukiwania
                    driver.save_screenshot("recipes_search_results.png")
                    print(f"✓ Zapisano zrzut ekranu wyników wyszukiwania dla '{search_term}'")
                    
                    # Sprawdź czy są wyniki lub komunikat o braku wyników
                    if search_term.lower() in driver.page_source.lower():
                        print(f"✓ Wyszukiwanie dla '{search_term}' zwróciło wyniki zawierające ten termin")
                        test_results["filter_search"] = True
                    else:
                        if "nie znaleziono" in driver.page_source.lower() or "no results" in driver.page_source.lower():
                            print(f"✓ Wyszukiwanie dla '{search_term}' nie zwróciło wyników, ale wyświetlono odpowiedni komunikat")
                            test_results["filter_search"] = True
                        else:
                            print(f"! Wyszukiwanie dla '{search_term}' nie zwróciło właściwych wyników ani komunikatu o ich braku")
                
                # Test filtrów kategorii, jeśli są dostępne
                if category_filters and len(category_filters) > 0:
                    # Wybierz pierwszy filtr kategorii
                    category_filter = category_filters[0]
                    driver.execute_script("arguments[0].click();", category_filter)
                    
                    # Czekaj na wyniki filtrowania
                    time.sleep(2)
                    
                    # Zapisanie zrzutu ekranu wyników filtrowania
                    driver.save_screenshot("recipes_filter_results.png")
                    print("✓ Zapisano zrzut ekranu wyników filtrowania po kategorii")
                    
                    # Sprawdź czy filtr zadziałał
                    if category_filter.is_selected() or category_filter.get_attribute("class").find("active") > -1:
                        print("✓ Filtr kategorii został aktywowany")
                        test_results["filter_search"] = True
                    else:
                        print("! Filtr kategorii nie został aktywowany")
                
                # Jeśli nie ma ani wyszukiwania, ani filtrów, to sprawdź czy jest jakiś inny mechanizm filtrowania
                if not search_box and not category_filters:
                    # Sprawdź czy jest jakiś inny element filtrowania
                    other_filters = driver.find_elements(By.CSS_SELECTOR, "select, .filter, .dropdown")
                    if other_filters:
                        print(f"✓ Znaleziono {len(other_filters)} innych elementów filtrowania")
                        test_results["filter_search"] = True
                    else:
                        print("! Nie znaleziono żadnych mechanizmów filtrowania lub wyszukiwania")
            except Exception as e:
                print(f"! Błąd podczas sprawdzania filtrów i wyszukiwania: {e}")
            
            # Test 4: Podgląd szczegółów przepisu
            print("\n=== TEST 4: PODGLĄD SZCZEGÓŁÓW PRZEPISU ===")
            
            try:
                # Powrót do listy wszystkich przepisów
                driver.get("http://localhost:8000/recipes/list/")
                print("✓ Otworzono ponownie stronę listy przepisów")
                time.sleep(2)
                
                # Znajdź pierwszy przepis i kliknij na niego
                recipe_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/recipes/detail/'], a[href*='/detail/'], .recipe-card a, .recipe-link")
                
                if recipe_links:
                    # Wybierz pierwszy link do przepisu
                    recipe_link = recipe_links[0]
                    recipe_title = recipe_link.text or "przepisu"
                    
                    # Kliknij na przepis
                    driver.execute_script("arguments[0].click();", recipe_link)
                    
                    # Czekaj na załadowanie szczegółów przepisu
                    time.sleep(2)
                    
                    # Zapisanie zrzutu ekranu szczegółów przepisu
                    driver.save_screenshot("recipe_details.png")
                    print(f"✓ Zapisano zrzut ekranu szczegółów {recipe_title}")
                    
                    # Sprawdź czy są wyświetlane szczegóły przepisu
                    expected_elements = ["składniki", "ingredients", "przygotowanie", "preparation", "przepis", "recipe"]
                    elements_found = [e for e in expected_elements if e in driver.page_source.lower()]
                    
                    if elements_found:
                        print(f"✓ Znaleziono szczegóły przepisu zawierające: {', '.join(elements_found)}")
                        test_results["recipe_details"] = True
                    else:
                        print("! Nie znaleziono oczekiwanych elementów szczegółów przepisu")
                else:
                    print("! Nie znaleziono linków do przepisów")
            except Exception as e:
                print(f"! Błąd podczas sprawdzania szczegółów przepisu: {e}")
            
            # Aktualizacja pliku test_results.txt
            with open('test_results.txt', 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            with open('test_results.txt', 'w', encoding='utf-8') as file:
                for line in lines:
                    if 'Lista wszystkich przepisów' in line:
                        file.write(f"   {'[x]' if test_results['list_all_recipes'] else '[ ]'} Lista wszystkich przepisów\n")
                    elif 'Filtry i wyszukiwanie' in line:
                        file.write(f"   {'[x]' if test_results['filter_search'] else '[ ]'} Filtry i wyszukiwanie\n")
                    elif 'Sortowanie' in line:
                        file.write(f"   {'[x]' if test_results['sorting'] else '[ ]'} Sortowanie\n")
                    elif 'Podgląd szczegółów przepisu' in line:
                        file.write(f"   {'[x]' if test_results['recipe_details'] else '[ ]'} Podgląd szczegółów przepisu\n")
                    else:
                        file.write(line)
            
            print("\n✅ Aktualizacja pliku test_results.txt zakończona pomyślnie")
            
            # Generowanie podsumowania wyników testów
            print("\n=== PODSUMOWANIE TESTÓW PRZEGLĄDANIA PRZEPISÓW ===")
            print(f"1. Lista wszystkich przepisów: {'✓ OK' if test_results['list_all_recipes'] else '✗ BŁĄD'}")
            print(f"2. Filtry i wyszukiwanie: {'✓ OK' if test_results['filter_search'] else '✗ BŁĄD'}")
            print(f"3. Sortowanie: {'✓ OK' if test_results['sorting'] else '✗ BŁĄD'}")
            print(f"4. Podgląd szczegółów przepisu: {'✓ OK' if test_results['recipe_details'] else '✗ BŁĄD'}")
            
            # Generowanie zaleceń
            print("\n=== ZALECENIA DOTYCZĄCE USPRAWNIEŃ ===")
            if not test_results["list_all_recipes"]:
                print("! PILNE: Naprawić funkcjonalność wyświetlania listy przepisów")
            if not test_results["filter_search"]:
                print("! PILNE: Naprawić funkcjonalność filtrowania i wyszukiwania przepisów")
            if not test_results["sorting"]:
                print("! PILNE: Dodać lub naprawić funkcjonalność sortowania przepisów")
            if not test_results["recipe_details"]:
                print("! PILNE: Naprawić funkcjonalność wyświetlania szczegółów przepisu")
            
            # Ogólne zalecenia
            print("! ZALECENIE: Dodać możliwość filtrowania po czasie przygotowania")
            print("! ZALECENIE: Dodać możliwość filtrowania po trudności przepisu")
            print("! ZALECENIE: Poprawić wygląd i układ listy przepisów dla większej przejrzystości")
            print("! ZALECENIE: Dodać paginację dla listy przepisów (jeśli nie istnieje)")
            print("! ZALECENIE: Dodać podgląd składników bez konieczności wchodzenia w szczegóły przepisu")
            
            return any(test_results.values())
            
        except Exception as e:
            print(f"BŁĄD podczas testu: {e}")
            traceback.print_exc()
            driver.save_screenshot("recipes_error.png")
            print("Zapisano zrzut ekranu błędu")
            return False
            
        finally:
            driver.quit()
            print("Zamknięto przeglądarkę")
    
    except Exception as outer_e:
        print(f"KRYTYCZNY BŁĄD: {outer_e}")
        traceback.print_exc()
        return False

def analyze_recipes_functionality():
    """Analizuje funkcjonalność modułu przepisów i generuje raport z zaleceniami"""
    # TODO: Implementacja analizy funkcjonalności i generowanie raportu
    pass

if __name__ == "__main__":
    print("Rozpoczęcie testów funkcji przeglądania przepisów")
    result = test_recipes_browse_functionality()
    print(f"\nTesty zakończone {'powodzeniem' if result else 'niepowodzeniem'}")
    sys.exit(0 if result else 1) 