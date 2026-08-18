"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
servidor_remoto.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Programa que ejecuta el servidor MCP propio en modo remoto utilizando el transporte Streamable HTTP.

             Publica el endpoint /mcp sobre el servidor HTTP de la libreria estandar y atiende el metodo POST para los
             mensajes JSON-RPC, el metodo GET para la verificacion de estado y el metodo DELETE para la terminacion
             explicita de una sesion. Genera un identificador de sesion durante la inicializacion y lo devuelve en el
             encabezado Mcp-Session-Id. Las notificaciones se confirman con el codigo 202 sin cuerpo. El puerto se toma
             de la variable de entorno PORT, lo que permite desplegar el servicio directamente en un entorno de nube.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import json
import os
import sys
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from nucleo_mcp import EstadoServidor, NOMBRE_SERVIDOR, VERSION_SERVIDOR, manejar

# Ruta del endpoint que atiende los mensajes del protocolo
RUTA_MCP = "/mcp"

# Tamaño maximo admitido para el cuerpo de una peticion
LIMITE_CUERPO = 1024 * 256

# Sesiones activas indexadas por el identificador entregado al cliente
SESIONES = {}


def registrar(texto):
    """Escribe una linea de diagnostico en la salida de error del proceso."""
    marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{marca}] {NOMBRE_SERVIDOR} {texto}", file=sys.stderr, flush=True)


class ManejadorMCP(BaseHTTPRequestHandler):
    """Manejador que traduce las peticiones HTTP en mensajes del protocolo MCP."""

    # Se declara HTTP/1.1 para permitir conexiones persistentes y facilitar el analisis en Wireshark
    protocol_version = "HTTP/1.1"
    server_version = f"{NOMBRE_SERVIDOR}/{VERSION_SERVIDOR}"

    def log_message(self, formato, *argumentos):
        """Redirige el registro interno del servidor hacia la salida de error."""
        registrar(f"{self.address_string()} {formato % argumentos}")

    def _responder_json(self, codigo, cuerpo, encabezados=None):
        """Envia una respuesta con contenido JSON."""
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        for clave, valor in (encabezados or {}).items():
            self.send_header(clave, valor)
        self.end_headers()
        self.wfile.write(datos)

    def _responder_vacio(self, codigo, encabezados=None):
        """Envia una respuesta sin cuerpo, utilizada para notificaciones y terminacion de sesion."""
        self.send_response(codigo)
        self.send_header("Content-Length", "0")
        for clave, valor in (encabezados or {}).items():
            self.send_header(clave, valor)
        self.end_headers()

    def _responder_texto(self, codigo, texto):
        """Envia una respuesta con contenido de texto plano."""
        datos = texto.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def _obtener_estado(self, identificador_sesion):
        """Recupera o crea el estado asociado a una sesion."""
        if identificador_sesion and identificador_sesion in SESIONES:
            return identificador_sesion, SESIONES[identificador_sesion]
        nuevo = uuid.uuid4().hex
        SESIONES[nuevo] = EstadoServidor()
        return nuevo, SESIONES[nuevo]

    def do_GET(self):
        """Atiende las verificaciones de estado y rechaza la apertura de flujos SSE."""
        if self.path in ("/", "/health", "/salud"):
            self._responder_texto(200, f"{NOMBRE_SERVIDOR} {VERSION_SERVIDOR} en ejecucion")
            return
        if self.path.startswith(RUTA_MCP):
            # Este servidor no mantiene flujos abiertos iniciados por el servidor
            self._responder_json(
                405,
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "el endpoint solo admite POST"}},
                {"Allow": "POST, DELETE"},
            )
            return
        self._responder_texto(404, "recurso no encontrado")

    def do_DELETE(self):
        """Termina de forma explicita la sesion indicada en el encabezado."""
        if not self.path.startswith(RUTA_MCP):
            self._responder_texto(404, "recurso no encontrado")
            return
        identificador = self.headers.get("Mcp-Session-Id")
        if identificador and identificador in SESIONES:
            SESIONES.pop(identificador)
            registrar(f"sesion {identificador} terminada por solicitud del cliente")
        self._responder_vacio(204)

    def do_POST(self):
        """Atiende los mensajes JSON-RPC enviados por el cliente."""
        if not self.path.startswith(RUTA_MCP):
            self._responder_texto(404, "recurso no encontrado")
            return

        longitud = int(self.headers.get("Content-Length") or 0)
        if longitud <= 0 or longitud > LIMITE_CUERPO:
            self._responder_json(
                400,
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "longitud de cuerpo invalida"}},
            )
            return

        crudo = self.rfile.read(longitud)
        try:
            mensaje = json.loads(crudo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._responder_json(
                400,
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "error de parseo del mensaje"}},
            )
            return

        # El identificador de sesion se genera al atender la solicitud initialize
        identificador_sesion, estado = self._obtener_estado(self.headers.get("Mcp-Session-Id"))
        registrar(f"metodo {mensaje.get('method')} id {mensaje.get('id')} sesion {identificador_sesion}")

        respuesta = manejar(mensaje, estado)
        encabezados = {"Mcp-Session-Id": identificador_sesion}
        if respuesta is None:
            # Las notificaciones se confirman con 202 y sin cuerpo segun el transporte Streamable HTTP
            self._responder_vacio(202, encabezados)
            return
        self._responder_json(200, respuesta, encabezados)


def main():
    """Levanta el servidor HTTP en el puerto indicado por la variable de entorno PORT."""
    puerto = int(os.environ.get("PORT", "8080"))
    direccion = os.environ.get("HOST", "0.0.0.0")
    servidor = ThreadingHTTPServer((direccion, puerto), ManejadorMCP)
    registrar(f"version {VERSION_SERVIDOR} escuchando en http://{direccion}:{puerto}{RUTA_MCP}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        registrar("ejecucion interrumpida por el usuario")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
