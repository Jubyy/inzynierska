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
            # Próba konwersji przez jednostkę bazową
            from recipes.models import MeasurementUnit
            base_units = MeasurementUnit.objects.filter(is_base=True)
            
            for base_unit in base_units:
                try:
                    # Konwersja: from_unit -> base_unit -> to_unit
                    to_base = UnitConversion.objects.get(from_unit=from_unit, to_unit=base_unit)
                    from_base = UnitConversion.objects.get(from_unit=base_unit, to_unit=to_unit)
                    
                    # Najpierw konwertuj do jednostki bazowej, potem do docelowej
                    base_amount = amount * to_base.ratio
                    return base_amount * from_base.ratio
                except UnitConversion.DoesNotExist:
                    continue
                    
            # Jeśli dotarliśmy tutaj, to konwersja nie jest możliwa
            raise ValueError(f"Nie można przekonwertować z {from_unit} na {to_unit}")

def get_common_units():
    """
    Zwraca listę popularnych jednostek miary wraz z ich symbolami i wartościami bazowymi.
    Te dane mogą być użyte do inicjalizacji bazy danych.
    
    Returns:
        list: Lista słowników zawierających informacje o jednostkach
    """
    return [
        {"name": "Gram", "symbol": "g", "is_base": True},
        {"name": "Kilogram", "symbol": "kg", "is_base": False},
        {"name": "Mililitr", "symbol": "ml", "is_base": True},
        {"name": "Litr", "symbol": "l", "is_base": False},
        {"name": "Łyżeczka", "symbol": "łyżeczka", "is_base": False},
        {"name": "Łyżka", "symbol": "łyżka", "is_base": False},
        {"name": "Szklanka", "symbol": "szklanka", "is_base": False},
        {"name": "Sztuka", "symbol": "szt", "is_base": False},
        {"name": "Szczypta", "symbol": "szczypta", "is_base": False},
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