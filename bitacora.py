"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
bitacora.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Modulo que implementa la bitacora de todas las interacciones entre el anfitrion y los servidores MCP.

             Registra cada solicitud, respuesta, notificacion y error del protocolo JSON-RPC con marca de tiempo,
             servidor involucrado, metodo invocado e identificador del mensaje. Los registros se mantienen en memoria
             para su consulta inmediata y se persisten en un archivo con formato JSON por linea que puede compararse
             posteriormente con las capturas realizadas en Wireshark.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import json
from datetime import datetime
from pathlib import Path

# Tipos de evento admitidos por la bitacora
SOLICITUD = "SOLICITUD"
RESPUESTA = "RESPUESTA"
NOTIFICACION = "NOTIFICACION"
ERROR = "ERROR"
SISTEMA = "SISTEMA"


class Bitacora:
    """Almacena y persiste el registro de las interacciones con los servidores MCP."""

    def __init__(self, directorio, ancho=120):
        self.directorio = Path(directorio)
        self.ancho = ancho
        self.registros = []
        self.directorio.mkdir(parents=True, exist_ok=True)
        # El nombre del archivo identifica de forma unica la sesion de trabajo
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.archivo = self.directorio / f"sesion_{marca}.jsonl"

    def registrar(self, tipo, servidor, metodo="", identificador=None, contenido=None, transporte=""):
        """Agrega un evento a la bitacora en memoria y lo escribe en el archivo de la sesion."""
        entrada = {
            "marca_tiempo": datetime.now().isoformat(timespec="milliseconds"),
            "tipo": tipo,
            "servidor": servidor,
            "transporte": transporte,
            "metodo": metodo,
            "id": identificador,
            "contenido": contenido,
        }
        self.registros.append(entrada)
        self._persistir(entrada)
        return entrada

    def _persistir(self, entrada):
        """Escribe una entrada individual en el archivo de la sesion."""
        try:
            with self.archivo.open("a", encoding="utf-8") as manejador:
                manejador.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        except OSError:
            # La falla de escritura no debe interrumpir la ejecucion del chatbot
            pass

    def total(self):
        """Devuelve la cantidad de eventos registrados en la sesion actual."""
        return len(self.registros)

    def ultimos(self, cantidad):
        """Devuelve los ultimos eventos registrados."""
        if cantidad <= 0:
            return []
        return self.registros[-cantidad:]

    def filtrar(self, servidor=None, tipo=None):
        """Devuelve los eventos que coinciden con el servidor o el tipo indicado."""
        resultado = []
        for entrada in self.registros:
            if servidor and entrada["servidor"] != servidor:
                continue
            if tipo and entrada["tipo"] != tipo:
                continue
            resultado.append(entrada)
        return resultado

    def formatear(self, entrada, detallado=True):
        """Convierte un evento en las lineas de texto que se muestran en la terminal."""
        cabecera = (
            f"[{entrada['marca_tiempo']}] "
            f"{entrada['tipo'].ljust(13)} "
            f"servidor: {str(entrada['servidor']).ljust(12)} "
            f"metodo: {str(entrada['metodo'] or '-').ljust(24)} "
            f"id: {entrada['id'] if entrada['id'] is not None else '-'}"
        )
        lineas = [cabecera]
        if detallado and entrada["contenido"] is not None:
            cuerpo = json.dumps(entrada["contenido"], ensure_ascii=False, indent=2)
            for linea in cuerpo.splitlines():
                # El contenido se recorta para no romper el ancho de la terminal
                lineas.append("    " + (linea if len(linea) <= self.ancho - 4 else linea[: self.ancho - 7] + "..."))
        return lineas

    def exportar(self, ruta):
        """Guarda la bitacora completa en un archivo JSON legible."""
        destino = Path(ruta)
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("w", encoding="utf-8") as manejador:
            json.dump(self.registros, manejador, ensure_ascii=False, indent=2)
        return destino

    def limpiar(self):
        """Elimina los registros mantenidos en memoria sin borrar el archivo de la sesion."""
        self.registros = []
