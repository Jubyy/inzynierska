def convert_units(amount, from_unit, to_unit):
    """
    Konwertuje ilość z jednej jednostki na drugą.
    
    Args:
        amount (float): Ilość do konwersji
        from_unit (MeasurementUnit): Jednostka źródłowa
        to_unit (MeasurementUnit): Jednostka docelowa
        
    Returns:
        float: Skonwertowana ilość
        
    Raises:
        ValueError: Jeśli konwersja nie jest możliwa
    """
    # Jeśli jednostki są takie same, nie ma potrzeby konwersji
    if from_unit == to_unit:
        return amount
    
    try:
        # Próba bezpośredniej konwersji
        from recipes.models import UnitConversion
        conversion = UnitConversion.objects.get(from_unit=from_unit, to_unit=to_unit)
        return amount * conversion.ratio
    except UnitConversion.DoesNotExist:
        # Próba odwrotnej konwersji
        try:
            conversion = UnitConversion.objects.get(from_unit=to_unit, to_unit=from_unit)
            return amount / conversion.ratio
        except UnitConversion.DoesNotExist:
            # Konwersja przez jednostki bazowe (bazując na typie i base_ratio)
            
            # Sprawdź czy obie jednostki są tego samego typu
            if from_unit.type == to_unit.type:
                # Konwersja za pomocą base_ratio
                # Najpierw konwertujemy amount do wartości bazowej (w g lub ml)
                base_amount = amount * from_unit.base_ratio
                # Następnie konwertujemy z wartości bazowej do jednostki docelowej
                return base_amount / to_unit.base_ratio
            else:
                # Konwersja między różnymi typami jednostek nie jest obsługiwana bezpośrednio
                raise ValueError(f"Nie można przekonwertować z {from_unit} na {to_unit} - różne typy jednostek")

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