# -*- coding: utf-8 -*-
import os


class FileManager:
    """
    Gestión de archivos de texto para los nodos de procesamiento.
    Carga el corpus (por ejemplo fragmentos de El Quijote o Mio Cid)
    para luego tokenizar y cuantificar.
    """

    @staticmethod
    def cargar_texto(ruta: str, codificacion: str = "utf-8") -> str:
        """
        Lee el contenido de un archivo de texto.

        Args:
            ruta: Ruta al archivo (.txt o similar).
            codificacion: Codificación del archivo (utf-8 por defecto).

        Returns:
            Contenido del archivo como string. Si el archivo no existe o
            hay error de lectura, devuelve una cadena vacía.
        """
        if not ruta or not os.path.isfile(ruta):
            return ""
        try:
            with open(ruta, "r", encoding=codificacion) as f:
                return f.read()
        except (OSError, UnicodeDecodeError):
            return ""
