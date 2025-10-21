# src/HppParser.py
import re
from enum import IntEnum

def parse_block_types_hpp(filepath):
    """
    Lee un archivo BlockTypes.hpp y extrae los tipos de bloque y sus colores.
    Devuelve una tupla: (BlockTypeEnum, block_colors_dict)
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"ERROR: No se pudo encontrar el archivo {filepath}")
        return None, None

    # --- 1. Extraer nombres de bloques del enum ---
    enum_pattern = re.compile(r'enum class BlockType.*?\{(.*?)\};', re.DOTALL)
    enum_match = enum_pattern.search(content)
    
    if not enum_match:
        print("ERROR: No se pudo encontrar 'enum class BlockType' en el archivo.")
        return None, None

    block_names = {}
    # Limpiamos y extraemos los nombres y sus valores
    for line in enum_match.group(1).split(','):
        line = line.strip()
        if not line or '//' in line:
            continue
        parts = line.split('=')
        name = parts[0].strip()
        if len(parts) > 1:
            value = int(parts[1].strip())
        else:
            # Si no hay valor explícito, se autoincrementa
            value = max(block_names.values()) + 1 if block_names else 0
        block_names[name] = value

    # Creamos el Enum dinámicamente
    GeneratedBlockType = IntEnum('BlockType', block_names)

    # --- 2. Extraer colores del struct ---
    color_pattern = re.compile(r'case BlockType::(.*?):.*?glm::vec3\((.*?)\)', re.DOTALL)
    color_matches = color_pattern.findall(content)

    block_colors = {}
    for name, color_str in color_matches:
        name = name.strip()
        # Convertimos "1.0f, 0.827f, 0.455f" a una tupla de floats (1.0, 0.827, 0.455)
        try:
            color_values = tuple(float(c.replace('f', '')) for c in color_str.split(','))
            # Usamos el enum que acabamos de crear para las claves del diccionario
            block_enum_member = GeneratedBlockType[name]
            block_colors[block_enum_member] = color_values
        except (ValueError, KeyError) as e:
            print(f"ADVERTENCIA: No se pudo procesar el color para el bloque '{name}'. Error: {e}")

    return GeneratedBlockType, block_colors