# src/BlockTypes.py
from src.HppParser import parse_block_types_hpp
from enum import IntEnum

def load_from_hpp(filepath):
    """
    Llama al parser y devuelve los tipos de bloque y colores.
    Si falla, devuelve valores por defecto para evitar que el programa se caiga.
    """
    BlockType, BLOCK_COLORS = parse_block_types_hpp(filepath)

    if BlockType is None:
        print("ADVERTENCIA: Se usarán tipos de bloque por defecto porque el parser falló.")
        BlockType = IntEnum('BlockType', {'Air': 0, 'Stone': 1})
        BLOCK_COLORS = {BlockType.Stone: (0.5, 0.5, 0.5)}
    
    # Aseguramos que 'Air' siempre exista, ya que es fundamental para la lógica
    if 'Air' not in BlockType.__members__:
         # Esto es improbable pero es una buena salvaguarda
        print("ADVERTENCIA: El tipo 'Air' no fue encontrado, se usará un valor por defecto.")
        # Aquí la lógica para añadirlo dinámicamente es compleja, es mejor usar los de por defecto
        BlockType = IntEnum('BlockType', {'Air': 0, 'Stone': 1})
        BLOCK_COLORS = {BlockType.Stone: (0.5, 0.5, 0.5)}

    if BlockType.Air not in BLOCK_COLORS:
        BLOCK_COLORS[BlockType.Air] = (0.0, 0.0, 0.0)
    
    return BlockType, BLOCK_COLORS