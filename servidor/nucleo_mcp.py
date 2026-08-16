"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
nucleo_mcp.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Modulo que implementa de forma manual el lado servidor del protocolo MCP sobre JSON-RPC 2.0.

             Define la especificacion de las diez herramientas expuestas por la cadena de farmacias, atiende los
             metodos initialize, notifications/initialized, ping, tools/list, tools/call, resources/list y
             prompts/list, valida los parametros recibidos y construye las respuestas del protocolo. El mismo nucleo
             es reutilizado por el servidor local sobre stdio y por el servidor remoto sobre Streamable HTTP, de modo
             que ambas variantes exponen exactamente la misma funcionalidad.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import json

import dominio

# Identidad del servidor que se anuncia durante la inicializacion
NOMBRE_SERVIDOR = "farmacia-mcp-uvg"
VERSION_SERVIDOR = "1.0.0"
TITULO_SERVIDOR = "Cadena de farmacias: orientacion farmaceutica y compra de medicamentos"

# Versiones del protocolo que este servidor es capaz de negociar
VERSIONES_SOPORTADAS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
VERSION_PREFERIDA = "2025-06-18"

# Codigos de error estandar de JSON-RPC utilizados por el servidor
ERROR_SOLICITUD_INVALIDA = -32600
ERROR_METODO_NO_ENCONTRADO = -32601
ERROR_PARAMETROS_INVALIDOS = -32602
ERROR_INTERNO = -32603

# Instrucciones que el servidor entrega al anfitrion durante la inicializacion
INSTRUCCIONES = (
    "Servidor de una cadena de farmacias. Permite consultar la ficha de un cliente con sus alergias, orientar segun "
    "sintomas, buscar medicamentos, revisar inventario por sucursal, verificar interacciones y registrar pedidos. "
    "Reglas obligatorias para el anfitrion: nunca afirmar un diagnostico; si evaluar_sintomas devuelve urgencia de "
    "atencion inmediata se debe derivar al servicio de emergencia y no ofrecer productos; los medicamentos con el "
    "campo requiere_receta en verdadero no se despachan sin receta vigente registrada; siempre reproducir el aviso "
    "clinico que devuelven las herramientas."
)

# Especificacion de las herramientas expuestas por el servidor
HERRAMIENTAS = [
    {
        "name": "consultar_cliente",
        "description": (
            "Devuelve la ficha de un cliente de la farmacia: nombre, edad, municipio, sucursal preferida, alergias "
            "declaradas, condiciones cronicas, recetas vigentes registradas y cantidad de pedidos activos."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "codigo_cliente": {"type": "string", "description": "Codigo del cliente con el formato CLI-1001"}
            },
            "required": ["codigo_cliente"],
        },
    },
    {
        "name": "evaluar_sintomas",
        "description": (
            "Clasifica la urgencia de un cuadro de sintomas y sugiere productos de venta libre cuando corresponde. "
            "Devuelve urgencia de atencion inmediata y ninguna sugerencia si detecta un signo de alarma, deriva a "
            "consulta profesional en menores de doce años y descarta los principios activos que choquen con las "
            "alergias indicadas. Siempre acompaña la respuesta de un aviso clinico que debe mostrarse al cliente."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sintomas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de sintomas descritos por el cliente en lenguaje natural",
                },
                "edad": {"type": "integer", "description": "Edad del cliente en años cumplidos"},
                "alergias": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alergias declaradas por el cliente, por ejemplo penicilina",
                },
            },
            "required": ["sintomas"],
        },
    },
    {
        "name": "buscar_medicamento",
        "description": (
            "Busca en el catalogo por principio activo, categoria terapeutica, indicacion o codigo. Devuelve "
            "presentacion, precio, edad minima, advertencias y si el producto exige receta medica."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "termino": {"type": "string", "description": "Texto a buscar, por ejemplo acetaminofen o fiebre"},
                "solo_venta_libre": {
                    "type": "boolean",
                    "description": "Si es verdadero excluye los medicamentos que requieren receta",
                },
                "categoria": {"type": "string", "description": "Categoria terapeutica a filtrar"},
            },
            "required": [],
        },
    },
    {
        "name": "listar_sucursales",
        "description": (
            "Devuelve las sucursales de la cadena con su direccion, horario, disponibilidad de farmaceutico de turno "
            "y si prestan servicio de entrega a domicilio."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "municipio": {"type": "string", "description": "Municipio a filtrar, por ejemplo Guatemala o Mixco"},
                "servicio_domicilio": {
                    "type": "boolean",
                    "description": "Si es verdadero devuelve solo las sucursales con entrega a domicilio",
                },
            },
            "required": [],
        },
    },
    {
        "name": "consultar_inventario",
        "description": (
            "Devuelve las existencias de un medicamento en una sucursal especifica o en toda la cadena, junto con su "
            "precio y la indicacion de si requiere receta."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "codigo_medicamento": {"type": "string", "description": "Codigo del medicamento con el formato MED-1001"},
                "codigo_sucursal": {"type": "string", "description": "Codigo de la sucursal con el formato SUC-01"},
            },
            "required": ["codigo_medicamento"],
        },
    },
    {
        "name": "verificar_interacciones",
        "description": (
            "Revisa si existen interacciones documentadas entre dos o mas medicamentos del catalogo y devuelve la "
            "severidad, el efecto esperado y la recomendacion para el farmaceutico."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "codigos_medicamentos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de codigos de medicamentos a evaluar, minimo dos",
                }
            },
            "required": ["codigos_medicamentos"],
        },
    },
    {
        "name": "crear_pedido",
        "description": (
            "Registra un pedido de compra para un cliente. Rechaza el pedido si algun medicamento exige receta y el "
            "cliente no la tiene vigente, si el principio activo choca con una alergia declarada, si el cliente no "
            "cumple la edad minima o si no hay inventario suficiente en la sucursal seleccionada."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "codigo_cliente": {"type": "string", "description": "Codigo del cliente con el formato CLI-1001"},
                "items": {
                    "type": "array",
                    "description": "Medicamentos solicitados con su cantidad",
                    "items": {
                        "type": "object",
                        "properties": {
                            "codigo_medicamento": {"type": "string", "description": "Codigo con el formato MED-1001"},
                            "cantidad": {"type": "integer", "description": "Unidades solicitadas, mayor a cero"},
                        },
                        "required": ["codigo_medicamento", "cantidad"],
                    },
                },
                "codigo_sucursal": {
                    "type": "string",
                    "description": "Sucursal donde se despacha, si se omite se usa la sucursal preferida del cliente",
                },
                "tipo_entrega": {
                    "type": "string",
                    "description": "Modalidad de entrega del pedido",
                    "enum": dominio.TIPOS_ENTREGA,
                },
            },
            "required": ["codigo_cliente", "items"],
        },
    },
    {
        "name": "consultar_pedido",
        "description": "Devuelve la informacion completa de un pedido a partir de su codigo.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "codigo_pedido": {"type": "string", "description": "Codigo del pedido con el formato PED-00001"}
            },
            "required": ["codigo_pedido"],
        },
    },
    {
        "name": "listar_pedidos",
        "description": "Devuelve los pedidos registrados, con la posibilidad de filtrarlos por cliente o por estado.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "codigo_cliente": {"type": "string", "description": "Codigo del cliente con el formato CLI-1001"},
                "estado": {
                    "type": "string",
                    "description": "Estado del pedido a filtrar",
                    "enum": dominio.ESTADOS_PEDIDO,
                },
            },
            "required": [],
        },
    },
    {
        "name": "actualizar_pedido",
        "description": "Cambia el estado de un pedido existente y agrega una nota de seguimiento a su historial.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "codigo_pedido": {"type": "string", "description": "Codigo del pedido con el formato PED-00001"},
                "estado": {
                    "type": "string",
                    "description": "Nuevo estado del pedido",
                    "enum": dominio.ESTADOS_PEDIDO,
                },
                "nota": {"type": "string", "description": "Nota de seguimiento asociada al cambio de estado"},
            },
            "required": ["codigo_pedido", "estado"],
        },
    },
]

# Correspondencia entre el nombre de la herramienta y la funcion del dominio que la resuelve
DESPACHADOR = {
    "consultar_cliente": lambda a: dominio.consultar_cliente(a["codigo_cliente"]),
    "evaluar_sintomas": lambda a: dominio.evaluar_sintomas(a["sintomas"], a.get("edad"), a.get("alergias")),
    "buscar_medicamento": lambda a: dominio.buscar_medicamento(
        a.get("termino"), a.get("solo_venta_libre"), a.get("categoria")
    ),
    "listar_sucursales": lambda a: dominio.listar_sucursales(a.get("municipio"), a.get("servicio_domicilio")),
    "consultar_inventario": lambda a: dominio.consultar_inventario(a["codigo_medicamento"], a.get("codigo_sucursal")),
    "verificar_interacciones": lambda a: dominio.verificar_interacciones(a["codigos_medicamentos"]),
    "crear_pedido": lambda a: dominio.crear_pedido(
        a["codigo_cliente"], a["items"], a.get("codigo_sucursal"), a.get("tipo_entrega", "retiro en sucursal")
    ),
    "consultar_pedido": lambda a: dominio.consultar_pedido(a["codigo_pedido"]),
    "listar_pedidos": lambda a: dominio.listar_pedidos(a.get("codigo_cliente"), a.get("estado")),
    "actualizar_pedido": lambda a: dominio.actualizar_pedido(a["codigo_pedido"], a["estado"], a.get("nota", "")),
}


class EstadoServidor:
    """Mantiene el estado de una sesion del servidor MCP."""

    def __init__(self):
        self.inicializado = False
        self.version_negociada = VERSION_PREFERIDA
        self.cliente = {}


def _respuesta(identificador, resultado):
    """Construye una respuesta exitosa de JSON-RPC."""
    return {"jsonrpc": "2.0", "id": identificador, "result": resultado}


def _error(identificador, codigo, mensaje, datos=None):
    """Construye una respuesta de error de JSON-RPC."""
    cuerpo = {"code": codigo, "message": mensaje}
    if datos is not None:
        cuerpo["data"] = datos
    return {"jsonrpc": "2.0", "id": identificador, "error": cuerpo}


def _contenido_texto(objeto):
    """Convierte el resultado de una herramienta en el bloque de contenido del protocolo."""
    return {"type": "text", "text": json.dumps(objeto, ensure_ascii=False, indent=2)}


def _manejar_initialize(identificador, parametros, estado):
    """Atiende la negociacion de version y capacidades del protocolo."""
    solicitada = parametros.get("protocolVersion", VERSION_PREFERIDA)
    # Si el cliente solicita una version conocida se acepta, de lo contrario se ofrece la preferida
    estado.version_negociada = solicitada if solicitada in VERSIONES_SOPORTADAS else VERSION_PREFERIDA
    estado.cliente = parametros.get("clientInfo", {})
    return _respuesta(
        identificador,
        {
            "protocolVersion": estado.version_negociada,
            "capabilities": {"tools": {"listChanged": False}, "logging": {}},
            "serverInfo": {"name": NOMBRE_SERVIDOR, "version": VERSION_SERVIDOR, "title": TITULO_SERVIDOR},
            "instructions": INSTRUCCIONES,
        },
    )


def _manejar_tools_call(identificador, parametros, estado):
    """Atiende la invocacion de una herramienta del servidor."""
    nombre = parametros.get("name")
    argumentos = parametros.get("arguments") or {}
    if not nombre:
        return _error(identificador, ERROR_PARAMETROS_INVALIDOS, "el parametro name es obligatorio")
    funcion = DESPACHADOR.get(nombre)
    if funcion is None:
        return _error(identificador, ERROR_PARAMETROS_INVALIDOS, f"la herramienta {nombre} no existe en este servidor")
    try:
        resultado = funcion(argumentos)
    except KeyError as detalle:
        # Los parametros obligatorios faltantes se devuelven como errores del protocolo
        return _error(identificador, ERROR_PARAMETROS_INVALIDOS, f"falta el parametro obligatorio {detalle}")
    except (TypeError, ValueError) as detalle:
        return _error(identificador, ERROR_PARAMETROS_INVALIDOS, f"los parametros recibidos no son validos: {detalle}")
    except dominio.ErrorDominio as detalle:
        # Los errores de negocio se devuelven dentro del resultado con la bandera isError
        return _respuesta(identificador, {"content": [{"type": "text", "text": str(detalle)}], "isError": True})
    except Exception as detalle:
        return _error(identificador, ERROR_INTERNO, f"error interno al ejecutar {nombre}: {detalle}")
    return _respuesta(identificador, {"content": [_contenido_texto(resultado)], "isError": False})


def manejar(mensaje, estado):
    """Procesa un mensaje JSON-RPC entrante y devuelve la respuesta o None si es una notificacion."""
    if not isinstance(mensaje, dict):
        return _error(None, ERROR_SOLICITUD_INVALIDA, "el mensaje no es un objeto JSON valido")
    if mensaje.get("jsonrpc") != "2.0":
        return _error(mensaje.get("id"), ERROR_SOLICITUD_INVALIDA, "el campo jsonrpc debe tener el valor 2.0")

    metodo = mensaje.get("method")
    identificador = mensaje.get("id")
    parametros = mensaje.get("params") or {}

    # Los mensajes sin metodo corresponden a respuestas del cliente y no requieren atencion
    if metodo is None:
        return None

    # Las notificaciones no generan respuesta segun la especificacion de JSON-RPC
    if identificador is None:
        if metodo == "notifications/initialized":
            estado.inicializado = True
        return None

    if metodo == "initialize":
        return _manejar_initialize(identificador, parametros, estado)
    if metodo == "ping":
        return _respuesta(identificador, {})
    if metodo == "tools/list":
        return _respuesta(identificador, {"tools": HERRAMIENTAS})
    if metodo == "tools/call":
        return _manejar_tools_call(identificador, parametros, estado)
    if metodo == "resources/list":
        return _respuesta(identificador, {"resources": []})
    if metodo == "resources/templates/list":
        return _respuesta(identificador, {"resourceTemplates": []})
    if metodo == "prompts/list":
        return _respuesta(identificador, {"prompts": []})
    if metodo == "logging/setLevel":
        return _respuesta(identificador, {})

    return _error(identificador, ERROR_METODO_NO_ENCONTRADO, f"el metodo {metodo} no esta implementado")
