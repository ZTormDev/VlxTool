# src/BlockTypes.py
from src.utils.HppParser import parse_block_types_hpp
from enum import IntEnum
from typing import Tuple, Dict, Any, Optional, cast


def load_from_hpp(filepath) -> Tuple[type, Dict[Any, tuple]]:
    """
    Llama al parser y devuelve los tipos de bloque y colores.
    Si falla, devuelve valores por defecto para evitar que el programa se caiga.
    """
    parsed = parse_block_types_hpp(filepath)

    # parse_block_types_hpp may return None or malformed data; validate it.
    BlockType = None
    BLOCK_COLORS = None
    if isinstance(parsed, tuple) and len(parsed) == 2:
        BlockType, BLOCK_COLORS = parsed
        if BLOCK_COLORS is None:
            BLOCK_COLORS = {}
    else:
        print("ADVERTENCIA: Se usarán tipos de bloque por defecto porque el parser falló.")
        BlockType = IntEnum('BlockType', {'Air': 0, 'Stone': 1})
        BLOCK_COLORS = {BlockType.Stone: (0.5, 0.5, 0.5)}
    
    # Aseguramos que 'Air' siempre exista, ya que es fundamental para la lógica
    # Enum.__members__ is a mappingproxy, not a plain dict; check for attribute and membership
    members = getattr(BlockType, '__members__', None)
    has_air = False
    if members is not None:
        try:
            has_air = 'Air' in members
        except Exception:
            has_air = False
    if not hasattr(BlockType, '__members__') or not has_air:
        # If parser produced something unexpected, fallback but try to preserve colors
        print("ADVERTENCIA: El tipo 'Air' no fue encontrado, se usará un valor por defecto.")
        # Preserve any parsed color values by re-mapping if possible
        existing_colors = BLOCK_COLORS if isinstance(BLOCK_COLORS, dict) else {}
        BlockType = IntEnum('BlockType', {'Air': 0, 'Stone': 1})
        # remap if a color value existed in the parsed dict, otherwise use default
        fallback_color = (0.5, 0.5, 0.5)
        if existing_colors:
            # take the first value (a tuple of floats)
            first_val = next(iter(existing_colors.values()))
            if isinstance(first_val, tuple) and len(first_val) >= 3:
                fallback_color = first_val
        BLOCK_COLORS = {BlockType.Stone: fallback_color}

    # Añadimos color para Air si falta
    if hasattr(BlockType, 'Air'):
        air_key = getattr(BlockType, 'Air')
        if air_key not in BLOCK_COLORS:
            # Default to transparent/empty for air
            BLOCK_COLORS[air_key] = (0.0, 0.0, 0.0)
    
    return cast(type, BlockType), BLOCK_COLORS