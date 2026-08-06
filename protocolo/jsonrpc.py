"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
jsonrpc.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Modulo que implementa de forma manual el formato de mensajes de JSON-RPC 2.0 utilizado por MCP.

             Construye solicitudes, notificaciones, respuestas y errores conforme a la especificacion publicada en
             jsonrpc.org, valida la estructura de los mensajes recibidos y expone los codigos de error estandar del
             protocolo. No se utiliza ninguna libreria o SDK que implemente MCP, todo el intercambio se arma y se
             interpreta en este modulo.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

# Version obligatoria del protocolo JSON-RPC segun la especificacion
VERSION = "2.0"

# Codigos de error estandar definidos por JSON-RPC 2.0
ERROR_PARSEO = -32700
ERROR_SOLICITUD_INVALIDA = -32600
ERROR_METODO_NO_ENCONTRADO = -32601
ERROR_PARAMETROS_INVALIDOS = -32602
ERROR_INTERNO = -32603


class ErrorJSONRPC(Exception):
    """Excepcion que representa un objeto de error devuelto por el par remoto."""

    def __init__(self, codigo, mensaje, datos=None):
        super().__init__(f"[{codigo}] {mensaje}")
        self.codigo = codigo
        self.mensaje = mensaje
        self.datos = datos


def solicitud(identificador, metodo, parametros=None):
    """Construye un objeto de solicitud JSON-RPC que espera una respuesta."""
    mensaje = {"jsonrpc": VERSION, "id": identificador, "method": metodo}
    # El campo params se omite cuando el metodo no recibe argumentos
    if parametros is not None:
        mensaje["params"] = parametros
    return mensaje


def notificacion(metodo, parametros=None):
    """Construye un objeto de notificacion JSON-RPC que no espera respuesta."""
    mensaje = {"jsonrpc": VERSION, "method": metodo}
    if parametros is not None:
        mensaje["params"] = parametros
    return mensaje


def respuesta(identificador, resultado):
    """Construye un objeto de respuesta exitosa JSON-RPC."""
    return {"jsonrpc": VERSION, "id": identificador, "result": resultado}


def respuesta_error(identificador, codigo, mensaje, datos=None):
    """Construye un objeto de respuesta con error JSON-RPC."""
    error = {"code": codigo, "message": mensaje}
    if datos is not None:
        error["data"] = datos
    return {"jsonrpc": VERSION, "id": identificador, "error": error}


def es_notificacion(mensaje):
    """Indica si un mensaje entrante corresponde a una notificacion."""
    return isinstance(mensaje, dict) and "method" in mensaje and "id" not in mensaje


def es_solicitud(mensaje):
    """Indica si un mensaje entrante corresponde a una solicitud."""
    return isinstance(mensaje, dict) and "method" in mensaje and "id" in mensaje


def es_respuesta(mensaje):
    """Indica si un mensaje entrante corresponde a una respuesta."""
    return isinstance(mensaje, dict) and "id" in mensaje and ("result" in mensaje or "error" in mensaje)


def validar_estructura(mensaje):
    """Verifica que el mensaje cumpla con la estructura minima de JSON-RPC 2.0."""
    if not isinstance(mensaje, dict):
        return False, "el mensaje no es un objeto JSON"
    if mensaje.get("jsonrpc") != VERSION:
        return False, "el campo jsonrpc no corresponde a la version 2.0"
    if "method" not in mensaje and "result" not in mensaje and "error" not in mensaje:
        return False, "el mensaje no contiene method, result ni error"
    return True, ""


def extraer_resultado(mensaje):
    """Devuelve el resultado de una respuesta o eleva la excepcion del error recibido."""
    if "error" in mensaje:
        error = mensaje["error"] or {}
        raise ErrorJSONRPC(error.get("code", ERROR_INTERNO), error.get("message", "error desconocido"), error.get("data"))
    return mensaje.get("result", {})
