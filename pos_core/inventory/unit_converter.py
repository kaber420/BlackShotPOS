# pos_core/inventory/unit_converter.py
from typing import Dict, List

# Definición de equivalencias a unidades base (g, ml, pz)
WEIGHT_UNITS: Dict[str, float] = {
    'g': 1.0,
    'kg': 1000.0,
    'oz': 28.3495,  # Onza de peso (dry ounce)
    'lb': 453.592
}

VOLUME_UNITS: Dict[str, float] = {
    'ml': 1.0,
    'L': 1000.0,
    'l': 1000.0, # alias
    'fl_oz': 29.5735, # Onza líquida (fluid ounce)
    'gal': 3785.41
}

UNIT_UNITS: Dict[str, float] = {
    'pz': 1.0,
    'ud': 1.0, # alias unidad
    'slice': 1.0 # rebanadas, etc
}

MEASURE_TYPES = {
    'weight': WEIGHT_UNITS,
    'volume': VOLUME_UNITS,
    'unit': UNIT_UNITS
}

def get_available_units(measure_type: str) -> List[str]:
    """Retorna las unidades disponibles para un tipo de medida dado."""
    if measure_type not in MEASURE_TYPES:
        raise ValueError(f"Tipo de medida inválido: {measure_type}")
    
    # Excluimos alias para la interfaz de usuario si es necesario, 
    # pero por ahora retornamos todas las claves.
    return list(MEASURE_TYPES[measure_type].keys())

def get_base_unit(measure_type: str) -> str:
    """Retorna la unidad base esperada para almacenar en base de datos."""
    if measure_type == 'weight':
        return 'g'
    elif measure_type == 'volume':
        return 'ml'
    elif measure_type == 'unit':
        return 'pz'
    raise ValueError(f"Tipo de medida inválido: {measure_type}")

def convert_to_base(quantity: float, input_unit: str, measure_type: str) -> float:
    """
    Convierte una cantidad dada en una unidad específica a su unidad base, 
    dependiendo de si es peso, volumen o unidad.
    """
    if measure_type not in MEASURE_TYPES:
        raise ValueError(f"Tipo de medida inválido: {measure_type}. Debe ser 'weight', 'volume', o 'unit'.")
        
    units_dict = MEASURE_TYPES[measure_type]
    
    if input_unit not in units_dict:
        raise ValueError(
            f"Unidad '{input_unit}' no es válida para medida tipo '{measure_type}'. "
            f"Unidades permitidas: {', '.join(units_dict.keys())}"
        )
        
    conversion_factor = units_dict[input_unit]
    return quantity * conversion_factor

def convert_units(quantity: float, from_unit: str, to_unit: str, measure_type: str) -> float:
    """
    Convierte una cantidad entre cualquier par de unidades del mismo tipo de medida.
    """
    if measure_type not in MEASURE_TYPES:
        raise ValueError(f"Tipo de medida inválido: {measure_type}")
        
    units_dict = MEASURE_TYPES[measure_type]
    
    if from_unit not in units_dict or to_unit not in units_dict:
        raise ValueError(f"Unidades {from_unit} o {to_unit} no válidas para {measure_type}")
        
    # Convertir a base primero
    value_in_base = quantity * units_dict[from_unit]
    # Convertir de base a destino
    return value_in_base / units_dict[to_unit]
