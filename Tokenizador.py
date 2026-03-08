# -*- coding: utf-8 -*-
"""
Módulo de tokenización para el proyecto SD 2526-2.
Transforma texto bruto en unidades procesables (tokens) y los convierte
en valores numéricos listos para la sonorización MIDI.
"""

import re
from typing import List, Callable, Optional


def limpiar_texto(texto: str, conservar_acentos: bool = True) -> str:
    """
    Normaliza el texto para que la tokenización sea consistente.
    Elimina caracteres que no aportan a la métrica (puntuación, símbolos)
    y convierte a minúsculas para que "Quijote" y "quijote" tengan el mismo valor.

    Args:
        texto: Cadena de entrada (puede ser una línea, párrafo o obra completa).
        conservar_acentos: Si es True, mantiene á, é, ñ, etc. para español.

    Returns:
        Texto en minúsculas y sin caracteres especiales.
    """
    if not texto or not isinstance(texto, str):
        return ""

    # Quitar todo lo que no sea letra, número o espacio (opcional: mantener acentos)
    if conservar_acentos:
        # Permitir letras con acento y ñ (rango Unicode básico para español)
        patron = r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ]"
    else:
        patron = r"[^\w\s]"

    texto_sin_simbolos = re.sub(patron, " ", texto)
    texto_sin_espacios_extra = re.sub(r"\s+", " ", texto_sin_simbolos)
    return texto_sin_espacios_extra.strip().lower()


def tokenizar_por_palabras(texto_limpio: str) -> List[str]:
    """
    Divide el texto en tokens por palabra. Ideal para una rítmica más rápida:
    cada palabra se puede mapear a una nota MIDI.

    Args:
        texto_limpio: Texto ya pasado por limpiar_texto().

    Returns:
        Lista de palabras (tokens).
    """
    if not texto_limpio:
        return []
    return texto_limpio.split()


def tokenizar_por_oraciones(texto: str) -> List[str]:
    """
    Divide el texto en oraciones para analizar cadencia y complejidad por frase.
    Útil para una sonorización más “respirable”, una nota o valor por oración.

    Args:
        texto: Texto en bruto (se limpia por oración, no se elimina la puntuación
               de corte: . ! ?).

    Returns:
        Lista de oraciones (sin normalizar a minúsculas aquí; se puede hacer después).
    """
    if not texto or not isinstance(texto, str):
        return []

    # Cortar por . ! ? y eliminar fragmentos vacíos
    oraciones = re.split(r"[.!?]+", texto)
    return [s.strip() for s in oraciones if s.strip()]


def cuantificar_por_longitud(tokens: List[str]) -> List[int]:
    """
    Asigna a cada token un valor numérico igual a su longitud.
    Palabras más largas → números más altos (útil para pitch o velocity).

    Args:
        tokens: Lista de strings (palabras u oraciones).

    Returns:
        Lista de enteros (longitud de cada token).
    """
    return [len(t) for t in tokens if t]


def cuantificar_por_ascii(tokens: List[str]) -> List[int]:
    """
    Asigna a cada token un valor numérico como suma de los códigos ASCII
    de sus caracteres. Da más variedad que solo la longitud.

    Args:
        tokens: Lista de strings (palabras u oraciones).

    Returns:
        Lista de enteros (suma de ord(c) para cada carácter).
    """
    return [sum(ord(c) for c in t) for t in tokens if t]


def normalizar_a_midi(valores: List[int], minimo_midi: int = 0, maximo_midi: int = 127) -> List[int]:
    """
    Función de transferencia: lleva los valores cuantificados al rango MIDI [0, 127].
    Si todos los valores son iguales, se devuelve un valor intermedio para evitar
    división por cero.

    Args:
        valores: Lista de enteros (por ejemplo, longitudes o sumas ASCII).
        minimo_midi: Límite inferior del rango MIDI.
        maximo_midi: Límite superior del rango MIDI.

    Returns:
        Lista de enteros en el rango [minimo_midi, maximo_midi].
    """
    if not valores:
        return []

    min_val = min(valores)
    max_val = max(valores)
    rango_val = max_val - min_val

    if rango_val == 0:
        # Todos iguales: centrar en la mitad del rango MIDI
        medio = (minimo_midi + maximo_midi) // 2
        return [medio] * len(valores)

    rango_midi = maximo_midi - minimo_midi
    return [
        minimo_midi + int((v - min_val) / rango_val * rango_midi)
        for v in valores
    ]


def pipeline_palabras(
    texto: str,
    metrica: str = "longitud",
    normalizar: bool = True,
    conservar_acentos: bool = True,
) -> tuple[List[str], List[int], Optional[List[int]]]:
    """
    Pipeline completo: limpieza → tokenización por palabras → cuantificación → opcional normalización MIDI.

    Args:
        texto: Texto en bruto.
        metrica: "longitud" o "ascii".
        normalizar: Si True, se aplica normalizar_a_midi a los valores.
        conservar_acentos: Se pasa a limpiar_texto.

    Returns:
        (tokens, valores_cuantificados, valores_midi o None).
    """
    limpio = limpiar_texto(texto, conservar_acentos=conservar_acentos)
    tokens = tokenizar_por_palabras(limpio)

    if metrica == "ascii":
        valores = cuantificar_por_ascii(tokens)
    else:
        valores = cuantificar_por_longitud(tokens)

    valores_midi = normalizar_a_midi(valores) if normalizar else None
    return tokens, valores, valores_midi


def pipeline_oraciones(
    texto: str,
    metrica: str = "longitud",
    normalizar: bool = True,
    conservar_acentos: bool = True,
) -> tuple[List[str], List[int], Optional[List[int]]]:
    """
    Pipeline: tokenización por oraciones → limpieza de cada una → cuantificación → opcional MIDI.

    Args:
        texto: Texto en bruto.
        metrica: "longitud" o "ascii".
        normalizar: Si True, se aplica normalizar_a_midi.
        conservar_acentos: Se pasa a limpiar_texto en cada oración.

    Returns:
        (oraciones_limpias, valores_cuantificados, valores_midi o None).
    """
    oraciones_bruto = tokenizar_por_oraciones(texto)
    oraciones_limpias = [limpiar_texto(s, conservar_acentos=conservar_acentos) for s in oraciones_bruto]
    oraciones_limpias = [s for s in oraciones_limpias if s]

    if metrica == "ascii":
        valores = cuantificar_por_ascii(oraciones_limpias)
    else:
        valores = cuantificar_por_longitud(oraciones_limpias)

    valores_midi = normalizar_a_midi(valores) if normalizar else None
    return oraciones_limpias, valores, valores_midi
