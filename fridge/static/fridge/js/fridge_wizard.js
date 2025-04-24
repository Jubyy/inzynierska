// Funkcje debugujące dla aplikacji lodówka
console.log("Plik fridge_wizard.js został załadowany");

// Sprawdź, czy jesteśmy w trybie debugowania
function isDebugMode() {
    // Sprawdzamy, czy element debug-info jest widoczny, co oznacza, że jesteśmy w trybie debug
    return $('.debug-info').length > 0;
}

// Funkcja do sprawdzania, czy Select2 został poprawnie załadowany
function checkSelect2() {
    if (typeof $.fn.select2 === 'function') {
        if (isDebugMode()) console.log("Select2 jest dostępny");
        return true;
    } else {
        if (isDebugMode()) console.error("Select2 nie jest dostępny! Sprawdź, czy biblioteka jest załadowana.");
        return false;
    }
}

// Funkcja do sprawdzania błędów AJAX
function setupAjaxErrorHandler() {
    $(document).ajaxError(function(event, jqXHR, settings, error) {
        console.error("Błąd AJAX: ", error);
        console.error("URL: ", settings.url);
        console.error("Status: ", jqXHR.status);
        try {
            console.error("Odpowiedź: ", JSON.parse(jqXHR.responseText));
        } catch (e) {
            console.error("Odpowiedź (niepoprawny JSON): ", jqXHR.responseText);
        }
        
        // Dodaj informację o błędzie do debug-info tylko w trybie debug
        if (isDebugMode()) {
            const debugInfo = $('.debug-info');
            if (debugInfo.length) {
                debugInfo.append(`<div class="alert alert-danger mt-2">
                    <p><strong>Błąd AJAX:</strong> ${error}</p>
                    <p><strong>URL:</strong> ${settings.url}</p>
                    <p><strong>Status:</strong> ${jqXHR.status}</p>
                    <p><strong>Odpowiedź:</strong> ${jqXHR.responseText}</p>
                </div>`);
            }
        }
    });
}

// Funkcja do debugowania konwersji
function testUnitConversion(ingredientId, amount, fromUnitId, toUnitId) {
    if (isDebugMode()) console.log(`Test konwersji: ${amount} jednostki #${fromUnitId} -> jednostka #${toUnitId} dla składnika #${ingredientId}`);
    
    $.ajax({
        url: "/fridge/ajax/convert/",
        data: {
            ingredient_id: ingredientId,
            amount: amount,
            from_unit: fromUnitId,
            to_unit: toUnitId
        },
        success: function(data) {
            if (isDebugMode()) console.log("Sukces konwersji: ", data);
            if (isDebugMode()) alert(`Wynik konwersji: ${amount} jednostki #${fromUnitId} = ${data.converted_amount} jednostki #${toUnitId}`);
        },
        error: function(xhr, status, error) {
            console.error("Błąd konwersji: ", error);
            console.error("Status: ", status);
            try {
                const response = JSON.parse(xhr.responseText);
                console.error("Szczegóły: ", response);
                if (isDebugMode()) alert(`Błąd konwersji: ${response.error || error}`);
            } catch (e) {
                console.error("Odpowiedź: ", xhr.responseText);
                if (isDebugMode()) alert(`Błąd konwersji: ${error}`);
            }
        }
    });
}

// Inicjalizacja składników z debugowaniem
function initIngredientsWithDebug() {
    if (isDebugMode()) console.log("Inicjalizacja Select2 dla składników...");
    
    if (!checkSelect2()) {
        if (isDebugMode()) alert("Biblioteka Select2 nie jest dostępna! Formularze mogą nie działać poprawnie.");
        return;
    }
    
    // Testowe ładowanie składników
    $.ajax({
        url: "/fridge/ajax/ingredient-search/",
        type: "GET",
        data: { term: "", list_all: true },
        success: function(data) {
            if (isDebugMode()) console.log("Pobrano składniki: ", data);
            if (data.results && data.results.length > 0) {
                if (isDebugMode()) console.log("Liczba dostępnych składników: " + data.results.length);
            } else {
                if (isDebugMode()) console.warn("Nie znaleziono żadnych składników!");
                if (isDebugMode()) alert("W bazie danych nie ma żadnych składników! Dodaj jakieś składniki, aby korzystać z lodówki.");
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
                        url: "/fridge/ajax/ingredient-search/",
                        dataType: 'json',
                        delay: 250,
                        data: function(params) {
                            return {
                                term: params.term || '',
                                list_all: !params.term
                            };
                        },
                        processResults: function(data) {
                            if (isDebugMode()) console.log("Wyniki wyszukiwania: ", data);
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
                    if (isDebugMode()) console.log("Wybrano składnik: ", $(this).val());
                    $('.wizard-content[data-step="1"] .next-step').prop('disabled', false);
                    
                    // Po wyborze składnika od razu załaduj jednostki
                    loadCompatibleUnits($(this).val());
                }).on('select2:clear', function() {
                    if (isDebugMode()) console.log("Wyczyszczono wybór składnika");
                    $('.wizard-content[data-step="1"] .next-step').prop('disabled', true);
                });
                
                if (isDebugMode()) console.log("Select2 dla składników zainicjalizowany pomyślnie");
                
                // Inicjalizacja Select2 dla jednostek
                $('#unit-select').select2({
                    theme: "bootstrap4",
                    width: '100%',
                    placeholder: "Wybierz jednostkę",
                    allowClear: true
                }).on('select2:select', function() {
                    if (isDebugMode()) console.log("Wybrano jednostkę: ", $(this).val());
                    $('.wizard-content[data-step="2"] .next-step').prop('disabled', false);
                }).on('select2:clear', function() {
                    if (isDebugMode()) console.log("Wyczyszczono wybór jednostki");
                    $('.wizard-content[data-step="2"] .next-step').prop('disabled', true);
                });
                
                // Funkcja do ładowania kompatybilnych jednostek
                function loadCompatibleUnits(ingredientId) {
                    if (isDebugMode()) console.log("Ładowanie jednostek dla składnika #" + ingredientId);
                    
                    $.ajax({
                        url: "/fridge/ajax/load-units/",
                        data: { 'ingredient_id': ingredientId },
                        success: function(data) {
                            if (isDebugMode()) console.log("Pobrano jednostki: ", data);
                            
                            const unitSelect = $('#unit-select');
                            unitSelect.empty();
                            unitSelect.append(new Option('', '', false, false));
                            
                            if (data.units && data.units.length > 0) {
                                data.units.forEach(function(unit) {
                                    const option = new Option(unit.name, unit.id, false, unit.id === data.default_unit);
                                    $(option).data('type', unit.type);
                                    $(option).data('symbol', unit.symbol);
                                    unitSelect.append(option);
                                });
                                
                                unitSelect.trigger('change');
                                
                                if (data.default_unit) {
                                    unitSelect.val(data.default_unit).trigger('change');
                                }
                            } else {
                                if (isDebugMode()) console.warn("Nie znaleziono jednostek dla składnika #" + ingredientId);
                            }
                        },
                        error: function(xhr, status, error) {
                            console.error("Błąd podczas pobierania jednostek: ", error);
                            if (isDebugMode()) {
                                console.error("Status: ", status);
                                console.error("Odpowiedź: ", xhr.responseText);
                            }
                        }
                    });
                }
                
            } catch (e) {
                console.error("Błąd podczas inicjalizacji Select2: ", e);
                if (isDebugMode()) alert("Wystąpił błąd podczas inicjalizacji formularza: " + e.message);
            }
        },
        error: function(xhr, status, error) {
            console.error("Błąd podczas pobierania składników: ", error);
            if (isDebugMode()) {
                console.error("Status: ", status);
                console.error("Odpowiedź: ", xhr.responseText);
                alert("Nie udało się pobrać składników z serwera. Sprawdź konsolę po szczegóły.");
            }
        }
    });
}

// Ładowanie kompatybilnych jednostek dla składnika
function loadCompatibleUnits(ingredientId) {
    const unitSelect = $('#unit-select');
    unitSelect.empty();
    unitSelect.prop('disabled', true);

    $.ajax({
        url: '/fridge/ajax/compatible_units/',
        data: {
            ingredient_id: ingredientId
        },
        success: function(data) {
            if (isDebugMode()) console.log("Pobrane jednostki: ", data);
            unitSelect.prop('disabled', false);

            // Dodaj jednostki do pola wyboru
            $.each(data, function(index, unit) {
                unitSelect.append(new Option(unit.text, unit.id));
            });

            // Jeśli jest tylko jedna jednostka, wybierz ją automatycznie
            if (data.length === 1) {
                unitSelect.val(data[0].id).trigger('change');
                if (isDebugMode()) console.log("Automatycznie wybrano jedyną jednostkę: ", data[0]);
            }
        },
        error: function(xhr, status, error) {
            console.error("Błąd ładowania jednostek: ", error);
            if (isDebugMode()) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    alert(`Błąd ładowania jednostek: ${response.error || error}`);
                } catch (e) {
                    alert(`Błąd ładowania jednostek: ${error}`);
                }
            }
        }
    });
}

// Dodaj przyciski pomocnicze do debugowania - tylko w trybie debugowania
function addDebugButtons() {
    if (!isDebugMode()) return;
    
    // Przycisk do testowania konwersji
    $('<button id="test-conversion" class="btn btn-info mt-2">Test konwersji</button>')
        .appendTo('.debug-info')
        .click(function(e) {
            e.preventDefault();
            const ingredientId = $('#ingredient-select').val();
            const fromUnitId = $('#unit-select').val();
            
            if (!ingredientId || !fromUnitId) {
                alert("Wybierz składnik i jednostkę źródłową!");
                return;
            }
            
            // Pobierz wszystkie jednostki dla tego składnika
            $.ajax({
                url: "/fridge/ajax/load-units/",
                data: { 'ingredient_id': ingredientId },
                success: function(data) {
                    if (data.units && data.units.length > 0) {
                        // Wybierz inną jednostkę niż źródłowa
                        const toUnitId = data.units.find(u => u.id != fromUnitId)?.id || data.units[0].id;
                        
                        // Wykonaj test konwersji
                        testUnitConversion(ingredientId, 1, fromUnitId, toUnitId);
                    } else {
                        alert("Brak jednostek dla wybranego składnika!");
                    }
                },
                error: function() {
                    alert("Błąd podczas pobierania jednostek!");
                }
            });
        });
    
    // Przycisk do wyświetlania szczegółów składnika
    $('<button id="show-ingredient-details" class="btn btn-info mt-2 ml-2">Szczegóły składnika</button>')
        .appendTo('.debug-info')
        .click(function(e) {
            e.preventDefault();
            const ingredientId = $('#ingredient-select').val();
            
            if (!ingredientId) {
                alert("Wybierz składnik!");
                return;
            }
            
            // Pobierz szczegóły składnika
            $.ajax({
                url: "/recipes/ajax/ingredient-details/",
                data: { 'ingredient_id': ingredientId },
                success: function(data) {
                    console.log("Szczegóły składnika: ", data);
                    
                    // Wyświetl informacje w modalu
                    let details = `<h5>Szczegóły składnika #${ingredientId}</h5>`;
                    details += `<p><strong>Nazwa:</strong> ${data.name || 'brak'}</p>`;
                    details += `<p><strong>Kategoria:</strong> ${data.category || 'brak'}</p>`;
                    details += `<p><strong>Typ jednostek:</strong> ${data.unit_type || 'brak'}</p>`;
                    details += `<p><strong>Domyślna jednostka:</strong> ${data.default_unit || 'brak'}</p>`;
                    details += `<p><strong>Gęstość:</strong> ${data.density || 'nie określono'} g/ml</p>`;
                    details += `<p><strong>Waga sztuki:</strong> ${data.piece_weight || 'nie określono'} g</p>`;
                    
                    // Dodaj informacje do debug-info
                    $('.debug-info').append(`<div class="alert alert-info mt-2">${details}</div>`);
                },
                error: function() {
                    alert("Błąd podczas pobierania szczegółów składnika!");
                }
            });
        });
}

// Inicjalizacja podczas ładowania dokumentu
$(document).ready(function() {
    if (isDebugMode()) console.log("Dokument załadowany, rozpoczynam inicjalizację...");
    
    // Zawsze ustaw obsługę błędów AJAX, ale komunikaty debugowania będą się pojawiać tylko w trybie debug
    setupAjaxErrorHandler();
    
    // Sprawdź, czy jesteśmy w trybie debugowania
    if (isDebugMode()) {
        // Dodaj przycisk do naprawy formularza tylko w trybie debugowania
        $('<button id="debug-form" class="btn btn-warning mt-2">Napraw formularz</button>')
            .appendTo('.card-header')
            .click(function(e) {
                e.preventDefault();
                if (isDebugMode()) console.log("Próba naprawy formularza...");
                initIngredientsWithDebug();
            });
            
        // Dodaj przyciski pomocnicze do debugowania
        addDebugButtons();
        
        if (isDebugMode()) console.log("Tryb debugowania aktywny - dodano przyciski pomocnicze");
    } else {
        // W trybie produkcyjnym inicjalizuj tylko niezbędne komponenty bez dodatkowego logu
        if (checkSelect2()) {
            // Podstawowa inicjalizacja Select2 dla składników
            $('#ingredient-select').select2({
                theme: "bootstrap4",
                width: '100%',
                placeholder: "Wpisz lub wybierz składnik...",
                allowClear: true,
                ajax: {
                    url: "/fridge/ajax/ingredient-search/",
                    dataType: 'json',
                    delay: 250,
                    data: function(params) {
                        return {
                            term: params.term || '',
                            list_all: !params.term
                        };
                    },
                    processResults: function(data) {
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
                $('.wizard-content[data-step="1"] .next-step').prop('disabled', false);
                // Po wyborze składnika załaduj jednostki
                loadCompatibleUnits($(this).val());
            }).on('select2:clear', function() {
                $('.wizard-content[data-step="1"] .next-step').prop('disabled', true);
            });
            
            // Podstawowa inicjalizacja Select2 dla jednostek
            $('#unit-select').select2({
                theme: "bootstrap4",
                width: '100%',
                placeholder: "Wybierz jednostkę",
                allowClear: true
            }).on('select2:select', function() {
                $('.wizard-content[data-step="2"] .next-step').prop('disabled', false);
                const unitSymbol = $(this).find(':selected').data('symbol');
                $('#unit-symbol').text(unitSymbol);
            }).on('select2:clear', function() {
                $('.wizard-content[data-step="2"] .next-step').prop('disabled', true);
            });
        }
    }
}); 