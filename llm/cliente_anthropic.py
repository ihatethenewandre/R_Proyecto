"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
cliente_anthropic.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Modulo que implementa el consumo directo de la API de mensajes del modelo de lenguaje.

             Construye la peticion HTTP hacia el endpoint de mensajes utilizando unicamente la libreria estandar,
             adjunta los encabezados de autenticacion y de version exigidos por el proveedor, envia el historial
             completo de la conversacion junto con el catalogo de herramientas MCP y devuelve la respuesta ya
             interpretada. Tambien traduce los codigos de error HTTP mas comunes a mensajes comprensibles.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import json
import urllib.error
import urllib.request


class ErrorLLM(Exception):
    """Excepcion que representa una falla en la comunicacion con el modelo de lenguaje."""


class ClienteAnthropic:
    """Cliente que conversa con el modelo de lenguaje a nivel de su API."""

    def __init__(self, api_key, modelo, url, version_api, max_tokens=2048, temperatura=0.4, tiempo_espera=120):
        self.api_key = api_key
        self.modelo = modelo
        self.url = url
        self.version_api = version_api
        self.max_tokens = max_tokens
        self.temperatura = temperatura
        self.tiempo_espera = tiempo_espera

    def disponible(self):
        """Indica si existe una clave de API configurada."""
        return bool(self.api_key)

    def _encabezados(self):
        """Arma los encabezados HTTP requeridos por la API de mensajes."""
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.version_api,
        }

    def enviar(self, mensajes, herramientas=None, sistema=None):
        """Envia el historial de la conversacion al modelo y devuelve la respuesta completa."""
        if not self.api_key:
            raise ErrorLLM("no se encontro la clave ANTHROPIC_API_KEY, definela en el archivo .env")

        carga = {
            "model": self.modelo,
            "max_tokens": self.max_tokens,
            "temperature": self.temperatura,
            "messages": mensajes,
        }
        if sistema:
            carga["system"] = sistema
        # El catalogo de herramientas MCP se expone al modelo con el formato de tool use
        if herramientas:
            carga["tools"] = herramientas

        cuerpo = json.dumps(carga, ensure_ascii=False).encode("utf-8")
        peticion = urllib.request.Request(self.url, data=cuerpo, headers=self._encabezados(), method="POST")
        try:
            with urllib.request.urlopen(peticion, timeout=self.tiempo_espera) as respuesta:
                return json.loads(respuesta.read().decode("utf-8"))
        except urllib.error.HTTPError as detalle:
            contenido = detalle.read().decode("utf-8", errors="replace")
            raise ErrorLLM(self._interpretar_error(detalle.code, contenido))
        except urllib.error.URLError as detalle:
            raise ErrorLLM(f"no fue posible contactar la API del modelo: {detalle.reason}")
        except TimeoutError:
            raise ErrorLLM(f"la API del modelo no respondio en {self.tiempo_espera} segundos")

    def _interpretar_error(self, codigo, contenido):
        """Traduce el codigo HTTP recibido a un mensaje descriptivo para el usuario."""
        try:
            detalle = json.loads(contenido).get("error", {}).get("message", contenido)
        except json.JSONDecodeError:
            detalle = contenido
        explicaciones = {
            400: "la peticion es invalida, revisa el nombre del modelo configurado en MODELO_LLM",
            401: "la clave de la API es invalida o fue revocada",
            403: "la clave de la API no tiene permisos sobre el modelo solicitado",
            404: "el modelo configurado no existe, revisa el valor de MODELO_LLM",
            429: "se alcanzo el limite de peticiones o se agoto el credito disponible",
            500: "el proveedor reporto un error interno, reintenta en unos segundos",
            529: "el servicio esta sobrecargado, reintenta en unos segundos",
        }
        base = explicaciones.get(codigo, "error no clasificado")
        return f"HTTP {codigo}, {base}. Detalle: {str(detalle)[:200]}"

    @staticmethod
    def extraer_texto(respuesta):
        """Concatena los bloques de texto devueltos por el modelo."""
        partes = []
        for bloque in respuesta.get("content", []):
            if bloque.get("type") == "text":
                partes.append(bloque.get("text", ""))
        return "\n".join(parte for parte in partes if parte.strip())

    @staticmethod
    def extraer_usos(respuesta):
        """Devuelve los bloques en los que el modelo solicita invocar una herramienta."""
        return [bloque for bloque in respuesta.get("content", []) if bloque.get("type") == "tool_use"]
