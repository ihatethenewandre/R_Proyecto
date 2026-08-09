"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
cliente_mcp.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Modulo que implementa el cliente del protocolo MCP sobre cualquiera de los transportes disponibles.

             Ejecuta el ciclo de vida completo del protocolo: negociacion de version y capacidades mediante el metodo
             initialize, envio de la notificacion notifications/initialized, descubrimiento de herramientas con
             tools/list e invocacion de herramientas con tools/call. Cada mensaje enviado y recibido se entrega a la
             bitacora para cumplir con el requerimiento de mantener el registro completo de las interacciones.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import bitacora as registro
from protocolo import jsonrpc
from protocolo.transporte_stdio import ErrorTransporte


class ClienteMCP:
    """Cliente que mantiene la conexion con un servidor MCP y expone sus herramientas."""

    def __init__(self, clave, nombre, transporte, log, version_protocolo, nombre_cliente, version_cliente):
        self.clave = clave
        self.nombre = nombre
        self.transporte = transporte
        self.log = log
        self.version_protocolo = version_protocolo
        self.nombre_cliente = nombre_cliente
        self.version_cliente = version_cliente
        self.contador = 0
        self.inicializado = False
        self.informacion_servidor = {}
        self.capacidades = {}
        self.herramientas = []

    def _siguiente_id(self):
        """Genera el identificador incremental que correlaciona solicitudes y respuestas."""
        self.contador += 1
        return self.contador

    def _registrar_pendientes(self, pendientes):
        """Registra en la bitacora los mensajes que el servidor envia por iniciativa propia."""
        for mensaje in pendientes:
            tipo = registro.NOTIFICACION if jsonrpc.es_notificacion(mensaje) else registro.SOLICITUD
            self.log.registrar(
                tipo,
                self.clave,
                mensaje.get("method", ""),
                mensaje.get("id"),
                mensaje,
                self.transporte.tipo,
            )

    def solicitar(self, metodo, parametros=None):
        """Envia una solicitud JSON-RPC al servidor y devuelve el resultado obtenido."""
        identificador = self._siguiente_id()
        mensaje = jsonrpc.solicitud(identificador, metodo, parametros)
        self.log.registrar(registro.SOLICITUD, self.clave, metodo, identificador, mensaje, self.transporte.tipo)
        try:
            respuesta, pendientes = self.transporte.solicitar(mensaje)
        except ErrorTransporte as detalle:
            self.log.registrar(registro.ERROR, self.clave, metodo, identificador, str(detalle), self.transporte.tipo)
            raise
        self._registrar_pendientes(pendientes)
        self.log.registrar(registro.RESPUESTA, self.clave, metodo, identificador, respuesta, self.transporte.tipo)
        valido, motivo = jsonrpc.validar_estructura(respuesta)
        if not valido:
            raise ErrorTransporte(f"respuesta con estructura invalida: {motivo}")
        return jsonrpc.extraer_resultado(respuesta)

    def notificar(self, metodo, parametros=None):
        """Envia una notificacion JSON-RPC al servidor."""
        mensaje = jsonrpc.notificacion(metodo, parametros)
        self.log.registrar(registro.NOTIFICACION, self.clave, metodo, None, mensaje, self.transporte.tipo)
        self.transporte.notificar(mensaje)

    def conectar(self):
        """Levanta el transporte y ejecuta la secuencia de inicializacion del protocolo."""
        self.log.registrar(
            registro.SISTEMA,
            self.clave,
            "conexion",
            None,
            {"servidor": self.nombre, "destino": self.transporte.descripcion()},
            self.transporte.tipo,
        )
        self.transporte.iniciar()
        # Primer mensaje del ciclo de vida: negociacion de version y capacidades
        resultado = self.solicitar(
            "initialize",
            {
                "protocolVersion": self.version_protocolo,
                "capabilities": {"roots": {"listChanged": False}, "sampling": {}},
                "clientInfo": {"name": self.nombre_cliente, "version": self.version_cliente},
            },
        )
        self.informacion_servidor = resultado.get("serverInfo", {})
        self.capacidades = resultado.get("capabilities", {})
        self.version_negociada = resultado.get("protocolVersion", self.version_protocolo)
        # Segundo mensaje del ciclo de vida: confirmacion de que el cliente quedo listo
        self.notificar("notifications/initialized")
        self.inicializado = True
        self.listar_herramientas()
        return resultado

    def listar_herramientas(self):
        """Consulta el catalogo de herramientas expuesto por el servidor."""
        if "tools" not in self.capacidades:
            self.herramientas = []
            return self.herramientas
        resultado = self.solicitar("tools/list", {})
        self.herramientas = resultado.get("tools", [])
        # Algunos servidores entregan el catalogo por paginas mediante un cursor
        cursor = resultado.get("nextCursor")
        while cursor:
            resultado = self.solicitar("tools/list", {"cursor": cursor})
            self.herramientas.extend(resultado.get("tools", []))
            cursor = resultado.get("nextCursor")
        return self.herramientas

    def llamar_herramienta(self, nombre, argumentos):
        """Invoca una herramienta del servidor y devuelve el resultado del protocolo."""
        return self.solicitar("tools/call", {"name": nombre, "arguments": argumentos or {}})

    def ping(self):
        """Verifica que el servidor siga respondiendo mensajes del protocolo."""
        return self.solicitar("ping", {})

    def desconectar(self):
        """Cierra la conexion con el servidor y registra el evento en la bitacora."""
        self.log.registrar(registro.SISTEMA, self.clave, "desconexion", None, {"servidor": self.nombre}, self.transporte.tipo)
        try:
            self.transporte.cerrar()
        except Exception:
            # El cierre nunca debe propagar excepciones hacia el menu principal
            pass
        self.inicializado = False
        self.herramientas = []
