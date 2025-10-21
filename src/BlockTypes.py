# src/BlockTypes.py
from src.HppParser import parse_block_types_hpp
from enum import IntEnum
from typing import Tuple, Dict, Any, Optional


def load_from_hpp(filepath) -> Tuple[type, Dict[Any, tuple]]:
    """
    Llama al parser y devuelve los tipos de bloque y colores.
    Si falla, devuelve valores por defecto para evitar que el programa se caiga.
    """
    parsed = parse_block_types_hpp(filepath)

    # parse_block_types_hpp may return None or malformed data; validate it.
    if (
        not isinstance(parsed, tuple)
        or len(parsed) != 2
        or parsed[0] is None
        or parsed[1] is None
    ):
        print("ADVERTENCIA: Se usarán tipos de bloque por defecto porque el parser falló.")
        BlockType = IntEnum('BlockType', {'Air': 0, 'Stone': 1})
        BLOCK_COLORS = {BlockType.Stone: (0.5, 0.5, 0.5)}
    else:
        BlockType, BLOCK_COLORS = parsed
        # Ensure BLOCK_COLORS is at least a dict
        if BLOCK_COLORS is None:
            BLOCK_COLORS = {}
    
    # Aseguramos que 'Air' siempre exista, ya que es fundamental para la lógica
    members = getattr(BlockType, '__members__', None)
    if not isinstance(members, dict) or 'Air' not in members:
        # Esto es improbable pero es una buena salvaguarda
        print("ADVERTENCIA: El tipo 'Air' no fue encontrado, se usará un valor por defecto.")
        BlockType = IntEnum('BlockType', {'Air': 0, 'Stone': 1})
        BLOCK_COLORS = {BlockType.Stone: (0.5, 0.5, 0.5)}

    # Añadimos color para Air si falta
    if hasattr(BlockType, 'Air'):
        air_key = getattr(BlockType, 'Air')
        if air_key not in BLOCK_COLORS:
            BLOCK_COLORS[air_key] = (0.0, 0.0, 0.0)
    
    return BlockType, BLOCK_COLORS