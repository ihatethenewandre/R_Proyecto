"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
servidor_local.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Programa que ejecuta el servidor MCP propio en modo local utilizando el transporte stdio.

             Lee mensajes JSON-RPC delimitados por salto de linea desde la entrada estandar, los entrega al nucleo del
             protocolo y escribe las respuestas en la salida estandar. La salida de error se reserva exclusivamente
             para el registro de diagnostico, tal como lo exige la especificacion del transporte stdio, de modo que el
             canal de datos nunca se contamine con mensajes que no pertenezcan al protocolo.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import json
import sys
from datetime import datetime

from nucleo_mcp import EstadoServidor, NOMBRE_SERVIDOR, VERSION_SERVIDOR, manejar


def registrar(texto):
    """Escribe una linea de diagnostico en la salida de error del proceso."""
    marca = datetime.now().strftime("%H:%M:%S")
    print(f"[{marca}] {NOMBRE_SERVIDOR} {texto}", file=sys.stderr, flush=True)


def responder(mensaje):
    """Serializa y escribe una respuesta en la salida estandar del proceso."""
    sys.stdout.write(json.dumps(mensaje, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    """Ciclo principal que atiende los mensajes recibidos por la entrada estandar."""
    estado = EstadoServidor()
    registrar(f"version {VERSION_SERVIDOR} en ejecucion sobre el transporte stdio")

    for linea in sys.stdin:
        texto = linea.strip()
        if not texto:
            continue
        try:
            mensaje = json.loads(texto)
        except json.JSONDecodeError as detalle:
            registrar(f"mensaje descartado por error de parseo: {detalle}")
            # El codigo -32700 corresponde al error de parseo definido por JSON-RPC
            responder({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "error de parseo del mensaje"}})
            continue

        registrar(f"mensaje recibido: metodo {mensaje.get('method')} id {mensaje.get('id')}")
        respuesta = manejar(mensaje, estado)
        if respuesta is not None:
            responder(respuesta)

    registrar("la entrada estandar se cerro, el servidor finaliza")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        registrar("ejecucion interrumpida por el usuario")
