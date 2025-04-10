// Funkcje debugujące dla aplikacji lodówka
console.log("Plik fridge_wizard.js został załadowany");

// Funkcja do sprawdzania, czy Select2 został poprawnie załadowany
function checkSelect2() {
    if (typeof $.fn.select2 === 'function') {
        console.log("Select2 jest dostępny");
        return true;
    } else {
        console.error("Select2 nie jest dostępny! Sprawdź, czy biblioteka jest załadowana.");
        return false;
    }
}

// Funkcja do sprawdzania błędów AJAX
function setupAjaxErrorHandler() {
    $(document).ajaxError(function(event, jqXHR, settings, error) {
        console.error("Błąd AJAX: ", error);
        console.error("URL: ", settings.url);
        console.error("Status: ", jqXHR.status);
        console.error("Odpowiedź: ", jqXHR.responseText);
        alert("Wystąpił błąd podczas komunikacji z serwerem. Sprawdź konsolę po szczegóły.");
    });
}

// Funkcja do inicjalizacji składników z debugowaniem
function initIngredientsWithDebug() {
    console.log("Inicjalizacja Select2 dla składników...");
    
    if (!checkSelect2()) {
        alert("Biblioteka Select2 nie jest dostępna! Formularze mogą nie działać poprawnie.");
        return;
    }
    
    // Testowe ładowanie składników
    $.ajax({
        url: "/fridge/ajax/ingredient_search/",
        type: "GET",
        data: { term: "", list_all: true },
        success: function(data) {
            console.log("Pobrano składniki: ", data);
            if (data.results && data.results.length > 0) {
                console.log("Liczba dostępnych składników: " + data.results.length);
            } else {
                console.warn("Nie znaleziono żadnych składników!");
                alert("W bazie danych nie ma żadnych składników! Dodaj jakieś składniki, aby korzystać z lodówki.");
            }
            
            // Spróbuj inicjalizować select2
            try {
                $('#ingredient-select').select2({
                    theme: "bootstrap4",
                    width: '100%',
                    placeholder: "Wpisz lub wybierz składnik...",
                    allowClear: true,
                    data: data.results.map(function(item) {
                        return {
                            id: item.id,
                            text: item.name
                        };
                    }),
                    ajax: {
                        url: "/fridge/ajax/ingredient_search/",
                        dataType: 'json',
                        delay: 250,
                        data: function(params) {
                            return {
                                term: params.term || '',
                                list_all: !params.term
                            };
                        },
                        processResults: function(data) {
                            console.log("Wyniki wyszukiwania: ", data);
                            return {
                                results: data.results.map(function(item) {
                                    return {
                                        id: item.id,
                                        text: item.name,
                                        category: item.category
                                    };
                                })
                            };
                        },
                        cache: true
                    }
                }).on('select2:select', function() {
                    console.log("Wybrano składnik: ", $(this).val());
                    $('.wizard-content[data-step="1"] .next-step').prop('disabled', false);
                }).on('select2:clear', function() {
                    console.log("Wyczyszczono wybór składnika");
                    $('.wizard-content[data-step="1"] .next-step').prop('disabled', true);
                });
                
                console.log("Select2 dla składników zainicjalizowany pomyślnie");
            } catch (e) {
                console.error("Błąd podczas inicjalizacji Select2: ", e);
            }
        },
        error: function(xhr, status, error) {
            console.error("Błąd podczas pobierania składników: ", error);
            console.error("Status: ", status);
            console.error("Odpowiedź: ", xhr.responseText);
            alert("Nie udało się pobrać składników z serwera. Sprawdź konsolę po szczegóły.");
        }
    });
}

// Inicjalizacja podczas ładowania dokumentu
$(document).ready(function() {
    console.log("Dokument załadowany, rozpoczynam inicjalizację...");
    setupAjaxErrorHandler();
    
    // Przycisk do naprawy formularza
    $('<button id="debug-form" class="btn btn-warning mt-2">Napraw formularz</button>')
        .appendTo('.card-header')
        .click(function(e) {
            e.preventDefault();
            console.log("Próba naprawy formularza...");
            initIngredientsWithDebug();
        });
    
    console.log("Przycisk naprawy dodany");
}); 