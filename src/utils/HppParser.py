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
    enum_pattern = re.compile(r'enum\s+class\s+BlockType[^\{]*\{(.*?)\};', re.DOTALL)
    enum_match = enum_pattern.search(content)

    if not enum_match:
        print("ERROR: No se pudo encontrar 'enum class BlockType' en el archivo.")
        return None, None

    body = enum_match.group(1)

    # Buscamos entradas del enum en forma: Name [= N] ,
    entry_pattern = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*(?:=\s*([0-9]+))?\s*(?:,|$)')
    block_names = {}
    next_value = 0
    for m in entry_pattern.finditer(body):
        name = m.group(1)
        val_str = m.group(2)
        if val_str is not None:
            val = int(val_str)
            next_value = val + 1
        else:
            val = next_value
            next_value += 1
        block_names[name] = val

    if not block_names:
        print("ERROR: No se pudieron extraer nombres de bloque del enum.")
        return None, None

    GeneratedBlockType = IntEnum('BlockType', block_names)

    # --- 2. Extraer colores del struct ---
    # Iteramos por cada "case BlockType::Name:" y buscamos el primer glm::vec3(...) después de él
    block_colors = {}
    case_pattern = re.compile(r'case\s+BlockType::([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)((?=case\s+BlockType::)|$)', re.DOTALL)
    vec3_pattern = re.compile(r'glm::vec3\s*\(([^\)]*)\)')

    for case_match in case_pattern.finditer(content):
        name = case_match.group(1).strip()
        body_after = case_match.group(2)
        vecs = vec3_pattern.findall(body_after)
        if not vecs:
            continue
        # Take the first vec3 (light color)
        color_str = vecs[0]
        try:
            color_values = tuple(float(c.replace('f', '')) for c in color_str.split(','))
            block_enum_member = GeneratedBlockType[name]
            block_colors[block_enum_member] = color_values
        except (ValueError, KeyError) as e:
            print(f"ADVERTENCIA: No se pudo procesar el color para el bloque '{name}'. Error: {e}")

    return GeneratedBlockType, block_colors