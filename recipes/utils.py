CONVERSION_TABLE = {
    ('szklanka', 'ml'): 250,
    ('łyżka', 'ml'): 15,
    ('łyżeczka', 'ml'): 5,
    ('kg', 'g'): 1000,
    ('g', 'kg'): 1/1000,
    ('ml', 'szklanka'): 1/250,
    ('ml', 'łyżka'): 1/15,
    ('ml', 'łyżeczka'): 1/5,
}

def convert_units(quantity, from_unit, to_unit):
    if from_unit == to_unit:
        return quantity

    key = (from_unit, to_unit)
    if key in CONVERSION_TABLE:
        return quantity * CONVERSION_TABLE[key]
    
    # Jeśli nie umiemy przekonwertować - zwracamy None (błąd)
    return None
