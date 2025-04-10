def convert_units(amount, from_unit, to_unit, ingredient=None):
    """
    Konwertuje ilość z jednej jednostki na drugą.
    
    Args:
        amount (float): Ilość do konwersji
        from_unit (MeasurementUnit): Jednostka źródłowa
        to_unit (MeasurementUnit): Jednostka docelowa
        ingredient (Ingredient, optional): Składnik, dla którego wykonywana jest konwersja
        
    Returns:
        float: Skonwertowana ilość
        
    Raises:
        ValueError: Jeśli konwersja nie jest możliwa
    """
    from decimal import Decimal
    
    # Sprawdź, czy jednostki nie są None
    if from_unit is None or to_unit is None:
        raise ValueError("Jednostki nie mogą być puste")
    
    # Upewnij się, że amount jest typu float i nie jest ujemny
    try:
        if isinstance(amount, str):
            amount = float(amount.replace(',', '.'))
        elif isinstance(amount, Decimal):
            amount = float(amount)
        else:
            amount = float(amount)
            
        if amount < 0:
            raise ValueError("Ilość nie może być ujemna")
    except (ValueError, TypeError):
        raise ValueError(f"Nieprawidłowa wartość: {amount}")
    
    # Jeśli jednostki są takie same, nie ma potrzeby konwersji
    if from_unit == to_unit:
        return amount
    
    # Jeśli podano składnik, spróbuj użyć specyficznej konwersji dla niego
    if ingredient is not None:
        try:
            from recipes.models import IngredientConversion
            ratio = IngredientConversion.get_conversion_ratio(ingredient, from_unit, to_unit)
            return float(amount) * float(ratio)
        except (ValueError, Exception) as e:
            # Jeśli nie można wykonać konwersji dla składnika, pomiń i spróbuj ogólnej konwersji
            pass
    
    try:
        # Próba bezpośredniej konwersji
        from recipes.models import UnitConversion
        conversion = UnitConversion.objects.get(from_unit=from_unit, to_unit=to_unit)
        # Zapewnij zgodność typów przed mnożeniem
        ratio = float(conversion.ratio)
        return amount * ratio
    except UnitConversion.DoesNotExist:
        # Próba odwrotnej konwersji
        try:
            conversion = UnitConversion.objects.get(from_unit=to_unit, to_unit=from_unit)
            # Zapewnij zgodność typów przed dzieleniem
            ratio = float(conversion.ratio)
            if ratio == 0:
                raise ValueError(f"Współczynnik konwersji nie może być zerowy")
            return amount / ratio
        except UnitConversion.DoesNotExist:
            # Konwersja przez jednostki bazowe (bazując na typie i base_ratio)
            
            # Sprawdź czy obie jednostki są tego samego typu
            if from_unit.type == to_unit.type:
                # Konwersja za pomocą base_ratio
                # Zapewnij zgodność typów 
                try:
                    from_ratio = float(from_unit.base_ratio)
                    to_ratio = float(to_unit.base_ratio)
                    
                    if to_ratio == 0:
                        raise ValueError(f"Współczynnik bazowy jednostki docelowej nie może być zerowy")
                    
                    # Najpierw konwertujemy amount do wartości bazowej (w g lub ml)
                    base_amount = amount * from_ratio
                    # Następnie konwertujemy z wartości bazowej do jednostki docelowej
                    return base_amount / to_ratio
                except (ValueError, TypeError, AttributeError) as e:
                    raise ValueError(f"Błąd konwersji: {str(e)}")
            else:
                # Obsługa konwersji między różnymi typami jednostek
                if hasattr(from_unit, 'type') and hasattr(to_unit, 'type'):
                    # Konwersja między sztukami a wagą/objętością wymaga dodatkowych informacji
                    if (from_unit.type == 'piece' and to_unit.type in ['weight', 'volume']) or \
                       (to_unit.type == 'piece' and from_unit.type in ['weight', 'volume']):
                        raise ValueError(f"Konwersja między {from_unit.type} a {to_unit.type} wymaga informacji o wadze sztuki")
                    
                    # Konwersja między wagą a objętością wymaga informacji o gęstości
                    if (from_unit.type == 'weight' and to_unit.type == 'volume') or \
                       (from_unit.type == 'volume' and to_unit.type == 'weight'):
                        raise ValueError(f"Konwersja między {from_unit.type} a {to_unit.type} wymaga informacji o gęstości")
                    
                    # Dla łyżek/łyżeczek, można zrobić przybliżoną konwersję
                    if from_unit.type == 'spoon' and to_unit.type in ['weight', 'volume']:
                        try:
                            # Łyżki/łyżeczki -> ml/g
                            base_amount = amount * float(from_unit.base_ratio)
                            return base_amount / float(to_unit.base_ratio)
                        except (ValueError, TypeError, AttributeError):
                            pass
                    
                    if to_unit.type == 'spoon' and from_unit.type in ['weight', 'volume']:
                        try:
                            # ml/g -> łyżki/łyżeczki
                            base_amount = amount * float(from_unit.base_ratio)
                            return base_amount / float(to_unit.base_ratio)
                        except (ValueError, TypeError, AttributeError):
                            pass
                            
                # Jeśli nie udało się przeprowadzić żadnej konwersji
                raise ValueError(f"Nie można przekonwertować z {from_unit} na {to_unit} - niekompatybilne typy jednostek")

def get_common_units():
    """
    Zwraca listę popularnych jednostek miary wraz z ich symbolami i wartościami bazowymi.
    Te dane mogą być użyte do inicjalizacji bazy danych.
    
    Returns:
        list: Lista słowników zawierających informacje o jednostkach
    """
    return [
        {"name": "Gram", "symbol": "g", "type": "weight", "base_ratio": 1.0, "is_common": True},
        {"name": "Kilogram", "symbol": "kg", "type": "weight", "base_ratio": 1000.0, "is_common": True},
        {"name": "Mililitr", "symbol": "ml", "type": "volume", "base_ratio": 1.0, "is_common": True},
        {"name": "Litr", "symbol": "l", "type": "volume", "base_ratio": 1000.0, "is_common": True},
        {"name": "Łyżeczka", "symbol": "łyżeczka", "type": "volume", "base_ratio": 5.0, "is_common": True},
        {"name": "Łyżka", "symbol": "łyżka", "type": "volume", "base_ratio": 15.0, "is_common": True},
        {"name": "Szklanka", "symbol": "szklanka", "type": "volume", "base_ratio": 250.0, "is_common": True},
        {"name": "Sztuka", "symbol": "szt", "type": "piece", "base_ratio": 1.0, "is_common": True},
        {"name": "Szczypta", "symbol": "szczypta", "type": "custom", "base_ratio": 0.5, "is_common": True},
    ]

def get_common_conversions():
    """
    Zwraca listę popularnych konwersji między jednostkami.
    Te dane mogą być użyte do inicjalizacji bazy danych.
    
    Returns:
        list: Lista słowników zawierających informacje o konwersjach
    """
    return [
        # Waga
        {"from": "kg", "to": "g", "ratio": 1000.0},
        
        # Objętość
        {"from": "l", "to": "ml", "ratio": 1000.0},
        {"from": "szklanka", "to": "ml", "ratio": 250.0},
        {"from": "łyżka", "to": "ml", "ratio": 15.0},
        {"from": "łyżeczka", "to": "ml", "ratio": 5.0},
        
        # Typowe konwersje kulinarne - przybliżone wartości
        {"from": "szklanka", "to": "g", "ratio": 200.0},  # dla mąki
        {"from": "łyżka", "to": "g", "ratio": 15.0},      # dla mąki
        {"from": "łyżeczka", "to": "g", "ratio": 5.0},    # dla mąki
    ] 