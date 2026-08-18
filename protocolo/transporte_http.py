"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
transporte_http.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Modulo que implementa el transporte Streamable HTTP del protocolo MCP para servidores remotos.

             Envia cada mensaje JSON-RPC como una peticion POST hacia el endpoint del servidor desplegado en la nube y
             administra el identificador de sesion que el servidor entrega en el encabezado Mcp-Session-Id. Reconoce
             respuestas con tipo de contenido application/json y tambien flujos text/event-stream, interpretando en
             este ultimo caso los eventos data que transportan los mensajes del protocolo. Se construye unicamente con
             la libreria estandar para que el trafico generado sea directamente observable en Wireshark.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import json
import urllib.error
import urllib.request

from protocolo.transporte_stdio import ErrorTransporte


class TransporteHTTP:
    """Canal de comunicacion con un servidor MCP remoto mediante Streamable HTTP."""

    def __init__(self, url, encabezados=None, tiempo_espera=90, version_protocolo="2025-06-18"):
        self.url = url
        self.encabezados_extra = dict(encabezados or {})
        self.tiempo_espera = tiempo_espera
        self.version_protocolo = version_protocolo
        self.sesion = None
        self.tipo = "http"
        self.errores = []

    def descripcion(self):
        """Devuelve la direccion del servidor remoto."""
        return self.url

    def iniciar(self):
        """Valida la direccion configurada antes de comenzar el intercambio de mensajes."""
        if not self.url or not self.url.startswith(("http://", "https://")):
            raise ErrorTransporte("la direccion del servidor remoto no es valida, debe iniciar con http o https")

    def activo(self):
        """El transporte HTTP no mantiene un proceso vivo, por lo que siempre se considera disponible."""
        return True

    def _construir_encabezados(self):
        """Arma los encabezados HTTP exigidos por el transporte Streamable HTTP."""
        encabezados = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": self.version_protocolo,
            "User-Agent": "anfitrion-uvg-redes/1.0",
        }
        # El identificador de sesion se adjunta en todas las peticiones posteriores a initialize
        if self.sesion:
            encabezados["Mcp-Session-Id"] = self.sesion
        encabezados.update(self.encabezados_extra)
        return encabezados

    def _interpretar_cuerpo(self, cuerpo, tipo_contenido):
        """Convierte el cuerpo de la respuesta HTTP en una lista de mensajes JSON-RPC."""
        texto = cuerpo.decode("utf-8", errors="replace").strip()
        if not texto:
            return []
        if "text/event-stream" in tipo_contenido:
            mensajes = []
            # Cada evento del flujo SSE transporta un mensaje JSON-RPC en su campo data
            for linea in texto.splitlines():
                if linea.startswith("data:"):
                    carga = linea[5:].strip()
                    if not carga:
                        continue
                    try:
                        mensajes.append(json.loads(carga))
                    except json.JSONDecodeError:
                        self.errores.append(carga)
            return mensajes
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError:
            raise ErrorTransporte(f"la respuesta del servidor no es JSON valido: {texto[:120]}")
        return datos if isinstance(datos, list) else [datos]

    def _peticion(self, mensaje):
        """Ejecuta la peticion POST y devuelve los mensajes recibidos del servidor."""
        cuerpo = json.dumps(mensaje, ensure_ascii=False).encode("utf-8")
        peticion = urllib.request.Request(self.url, data=cuerpo, headers=self._construir_encabezados(), method="POST")
        try:
            with urllib.request.urlopen(peticion, timeout=self.tiempo_espera) as respuesta:
                # El servidor entrega el identificador de sesion al atender la solicitud initialize
                sesion = respuesta.headers.get("Mcp-Session-Id")
                if sesion:
                    self.sesion = sesion
                tipo_contenido = respuesta.headers.get("Content-Type", "")
                if respuesta.status == 202:
                    return []
                return self._interpretar_cuerpo(respuesta.read(), tipo_contenido)
        except urllib.error.HTTPError as detalle:
            contenido = detalle.read().decode("utf-8", errors="replace")
            raise ErrorTransporte(f"el servidor remoto devolvio HTTP {detalle.code}: {contenido[:200]}")
        except urllib.error.URLError as detalle:
            raise ErrorTransporte(f"no fue posible contactar al servidor remoto: {detalle.reason}")
        except TimeoutError:
            raise ErrorTransporte(f"el servidor remoto no respondio en {self.tiempo_espera} segundos")

    def solicitar(self, mensaje, tiempo_espera=None):
        """Envia una solicitud y devuelve la respuesta asociada a su identificador."""
        if tiempo_espera:
            self.tiempo_espera = tiempo_espera
        identificador = mensaje.get("id")
        mensajes = self._peticion(mensaje)
        pendientes = []
        for recibido in mensajes:
            if recibido.get("id") == identificador and ("result" in recibido or "error" in recibido):
                return recibido, pendientes
            pendientes.append(recibido)
        raise ErrorTransporte("el servidor remoto no devolvio una respuesta para la solicitud enviada")

    def notificar(self, mensaje):
        """Envia una notificacion que el servidor confirma con el codigo HTTP 202."""
        self._peticion(mensaje)

    def diagnostico(self, cantidad=10):
        """Devuelve las ultimas cargas que no pudieron interpretarse."""
        return self.errores[-cantidad:]

    def cerrar(self):
        """Solicita la terminacion de la sesion mediante el metodo DELETE."""
        if not self.sesion:
            return
        peticion = urllib.request.Request(self.url, headers=self._construir_encabezados(), method="DELETE")
        try:
            with urllib.request.urlopen(peticion, timeout=10):
                pass
        except (urllib.error.URLError, TimeoutError, OSError):
            # La terminacion de sesion es opcional, por lo que un fallo no interrumpe el cierre
            pass
        self.sesion = None
