import json
import re

def normalize_cost(value_str: str) -> float:
    """Maneja formatos como '(23)' -> -23.0 o '1,850' -> 1850.0"""
    if not value_str or value_str == "None": 
        return 0.0
    s = value_str.replace(',', '').strip()
    
    # Detectar formato (número) = negativo
    if s.startswith('(') and s.endswith(')'):
        val = re.search(r"(\d+\.?\d*)", s)
        return -float(val.group(1)) if val else 0.0
    
    val = re.search(r"(\d+\.?\d*)", s)
    return float(val.group(1)) if val else 0.0

def normalize_tonnes(value_str: str) -> float:
    """
    Convierte toneladas a formato numérico consistente.
    
    REGLAS CRÍTICAS:
    - "4.1 Mt" o "4.1 million tonnes" → 4,100,000.0 (4.1 millones)
    - "1,515 kt" o "1515 thousand tonnes" → 1,515,000.0 (1.515 millones)
    - "467 kt" → 467,000.0
    - Si no hay unidad pero el número es pequeño (< 100), asumir Mt
    """
    if not value_str or value_str in ["None", "na", "-"]: 
        return 0.0
    
    # Quitar comas ANTES de buscar el número
    s = value_str.lower().replace(',', '').strip()
    match = re.search(r"(\d+\.?\d*)", s)
    if not match: 
        return 0.0
    
    num = float(match.group(1))
    
    # Identificar unidades
    if 'mt' in s or 'million' in s:
        return round(num * 1_000_000, 0)
    
    if 'kt' in s or 'thousand' in s:
        return round(num * 1_000, 0)
    
    # NUEVA REGLA: Si el número es pequeño (< 100) y no tiene unidad,
    # probablemente sea Mt (como en "4.1" de la Tabla 14-5)
    if num < 100 and 'kt' not in s and 'mt' not in s:
        return round(num * 1_000_000, 0)
    
    return num

def normalize_ounces(value_str: str) -> float:
    """
    Convierte onzas a formato numérico.
    
    REGLAS:
    - "1,893 koz" → 1,893,000.0
    - "597 koz" → 597,000.0
    - Siempre retorna onzas completas, no en miles
    """
    if not value_str or value_str == "None": 
        return 0.0
    
    s = value_str.lower().replace(',', '').strip()
    match = re.search(r"(\d+\.?\d*)", s)
    if not match: 
        return 0.0
    
    num = float(match.group(1))
    
    # Identificar unidades
    if 'moz' in s or 'million' in s:
        return round(num * 1_000_000, 0)
    
    if 'koz' in s or 'kilo' in s:
        return round(num * 1_000, 0)
    
    # Si el número está entre 500-5000 sin unidad, asumir koz
    if 500 < num < 5000 and 'oz' not in s:
        return round(num * 1_000, 0)
    
    return num

def clean_llm_text(text: str) -> str:
    """
    Limpia el texto extraído del PDF antes de enviarlo al LLM 
    para eliminar ruidos comunes de OCR.
    """
    # Eliminar frases como "Page 1 of 61" o "NI 43-101 Technical Report"
    text = re.sub(r"Page \d+ of \d+", "", text)
    text = re.sub(r"NI 43-101 Technical Report", "", text, flags=re.IGNORECASE)
    # Eliminar múltiples espacios en blanco
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def save_to_json(data: dict, filename: str):
    """Guarda diccionarios en formato JSON."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✓ Archivo guardado exitosamente en {filename}")
    except Exception as e:
        print(f"✗ Error al guardar el archivo: {e}")

def validate_extraction(data: dict) -> dict:
    """
    Valida que la extracción tenga los datos esperados.
    Retorna un reporte de validación.
    """
    validation = {
        "status": "OK",
        "warnings": [],
        "errors": []
    }
    
    # Validar metadata
    if not data.get("metadata"):
        validation["errors"].append("Metadata faltante")
    elif not data["metadata"].get("qualified_persons"):
        validation["warnings"].append("Qualified persons no extraídos")
    
    # Validar tablas críticas
    critical_tables = {
        "vein_dimensions": 4,
        "mining_titles": 11,
        "drilling_summary": 13,
        "metallurgy_history": 5,
        "data_availability": 10,
        "resources": 4,
        "reserves": 3
    }
    
    for table, expected_count in critical_tables.items():
        actual = len(data.get(table, []))
        if actual == 0:
            validation["errors"].append(f"{table}: VACÍA (esperado {expected_count} registros)")
        elif actual < expected_count:
            validation["warnings"].append(f"{table}: {actual}/{expected_count} registros")
    
    # Validar unidades de recursos/reservas
    for resource in data.get("resources", []):
        if resource.get("tonnes", 0) < 1_000_000:
            validation["warnings"].append(f"Resources tonnes sospechosamente bajo: {resource['tonnes']}")
    
    for reserve in data.get("reserves", []):
        if reserve.get("tonnes", 0) < 500_000:
            validation["warnings"].append(f"Reserves tonnes sospechosamente bajo: {reserve['tonnes']}")
    
    if validation["errors"]:
        validation["status"] = "ERROR"
    elif validation["warnings"]:
        validation["status"] = "WARNING"
    
    return validation