"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
configuracion.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Modulo que centraliza los parametros de configuracion del anfitrion MCP.

             Carga las variables de entorno desde el archivo .env sin utilizar librerias externas, define las rutas
             base del proyecto, los parametros de conexion con la API del modelo de lenguaje, la version del protocolo
             MCP a negociar y el mensaje de sistema que gobierna el comportamiento del chatbot.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import os
import subprocess
import sys
from pathlib import Path

# Directorio raiz del proyecto, calculado a partir de la ubicacion de este archivo
RAIZ = Path(__file__).resolve().parent


def cargar_env(ruta=None):
    """Lee el archivo .env y coloca sus valores en las variables de entorno del proceso."""
    archivo = Path(ruta) if ruta else RAIZ / ".env"
    if not archivo.exists():
        return False
    with archivo.open("r", encoding="utf-8") as manejador:
        for linea in manejador:
            texto = linea.strip()
            # Se ignoran las lineas vacias y los comentarios
            if not texto or texto.startswith("#") or "=" not in texto:
                continue
            clave, valor = texto.split("=", 1)
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")
            # Las variables ya definidas en el sistema tienen prioridad sobre el archivo
            if clave and clave not in os.environ:
                os.environ[clave] = valor
    return True


# La carga se realiza al importar el modulo para que el resto del proyecto vea los valores
ENV_CARGADO = cargar_env()

# Credenciales y parametros del modelo de lenguaje
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
URL_API_LLM = os.environ.get("URL_API_LLM", "https://api.anthropic.com/v1/messages")
VERSION_API_LLM = os.environ.get("VERSION_API_LLM", "2023-06-01")
MODELO_LLM = os.environ.get("MODELO_LLM", "claude-sonnet-4-5")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "2048"))
TEMPERATURA = float(os.environ.get("TEMPERATURA", "0.4"))
TIEMPO_ESPERA_LLM = int(os.environ.get("TIEMPO_ESPERA_LLM", "120"))

# Parametros del protocolo MCP
VERSION_PROTOCOLO = os.environ.get("VERSION_PROTOCOLO", "2025-06-18")
NOMBRE_CLIENTE = os.environ.get("NOMBRE_CLIENTE", "anfitrion-uvg-redes")
VERSION_CLIENTE = os.environ.get("VERSION_CLIENTE", "1.0.0")
TIEMPO_ESPERA_MCP = int(os.environ.get("TIEMPO_ESPERA_MCP", "90"))

# Numero maximo de ciclos de razonamiento con herramientas por cada consulta del usuario
MAX_ITERACIONES_HERRAMIENTAS = int(os.environ.get("MAX_ITERACIONES_HERRAMIENTAS", "8"))

# Rutas de trabajo utilizadas por el proyecto
ARCHIVO_SERVIDORES = RAIZ / os.environ.get("ARCHIVO_SERVIDORES", "servidores.json")
DIRECTORIO_BITACORA = RAIZ / os.environ.get("DIRECTORIO_BITACORA", "bitacora")
ESPACIO_TRABAJO = RAIZ / os.environ.get("ESPACIO_TRABAJO", "espacio_trabajo")

# Direccion del servidor MCP remoto desplegado en la nube
URL_MCP_REMOTO = os.environ.get("URL_MCP_REMOTO", "")

# Interprete de Python utilizado para levantar el servidor MCP propio en modo local
INTERPRETE_PYTHON = sys.executable

# Mensaje de sistema que define el rol y las reglas de respuesta del chatbot
MENSAJE_SISTEMA = (
    "Eres el anfitrion de un chatbot de consola desarrollado para el curso de Redes de la Universidad del Valle de "
    "Guatemala. Coordinas varios servidores conectados mediante JSON-RPC 2.0 y decides cuando invocar sus "
    "herramientas. Uno de esos servidores atiende a los clientes de una cadena de farmacias. "
    "Reglas generales: responde siempre en español; se claro, breve y tecnico; nunca inventes resultados de una "
    "herramienta, si necesitas un dato que una herramienta puede entregar, invocala; explica en una linea que "
    "herramienta usaste y por que antes de dar el resultado final; si una herramienta devuelve un error, informa el "
    "error textual y propone una alternativa; no utilices emojis ni formato markdown pesado, la salida se imprime en "
    "una terminal de 120 caracteres de ancho. "
    "Reglas obligatorias del escenario de farmacia: no emites diagnosticos ni sustituyes a un profesional de salud; "
    "antes de sugerir cualquier producto invoca evaluar_sintomas y respeta su clasificacion de urgencia; si la "
    "urgencia es de atencion inmediata, deriva al servicio de emergencia y no ofrezcas ningun medicamento; nunca "
    "ofrezcas ni intentes despachar un medicamento cuyo campo requiere_receta sea verdadero si el cliente no tiene la "
    "receta vigente registrada; consulta las alergias del cliente antes de armar un pedido; verifica interacciones "
    "cuando el pedido lleve mas de un medicamento; y reproduce siempre al cliente el aviso clinico que devuelven las "
    "herramientas."
)


def resumen():
    """Devuelve la lista de parametros activos para mostrarlos en pantalla."""
    return [
        ("Archivo .env", "cargado" if ENV_CARGADO else "no encontrado"),
        ("Endpoint del modelo", URL_API_LLM),
        ("Modelo configurado", MODELO_LLM),
        ("Maximo de tokens", str(MAX_TOKENS)),
        ("Version del protocolo", VERSION_PROTOCOLO),
        ("Nombre del cliente", f"{NOMBRE_CLIENTE} {VERSION_CLIENTE}"),
        ("Archivo de servidores", str(ARCHIVO_SERVIDORES)),
        ("Directorio de bitacora", str(DIRECTORIO_BITACORA)),
        ("Espacio de trabajo", str(ESPACIO_TRABAJO)),
    ]


def preparar_directorios():
    """Crea los directorios de trabajo requeridos e inicializa el repositorio del espacio de trabajo."""
    DIRECTORIO_BITACORA.mkdir(parents=True, exist_ok=True)
    ESPACIO_TRABAJO.mkdir(parents=True, exist_ok=True)
    # El servidor de Git necesita que el directorio sea un repositorio, por lo que se inicializa si no lo es
    if not (ESPACIO_TRABAJO / ".git").exists():
        try:
            subprocess.run(
                ["git", "init", str(ESPACIO_TRABAJO)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            # Si Git no esta instalado el resto del programa sigue funcionando sin ese servidor
            pass
