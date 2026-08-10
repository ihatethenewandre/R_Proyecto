"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
administrador.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Modulo que coordina multiples clientes MCP en representacion del anfitrion.

             Lee las definiciones de servidores desde el archivo de configuracion, resuelve los marcadores de ruta,
             construye el transporte que corresponde a cada servidor, administra las conexiones y desconexiones, y
             consolida el catalogo de herramientas de todos los servidores en un solo listado apto para enviarse al
             modelo de lenguaje. Los nombres se prefijan con la clave del servidor para evitar colisiones entre
             herramientas homonimas.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import json
import re
from pathlib import Path

import configuracion
from protocolo.cliente_mcp import ClienteMCP
from protocolo.transporte_http import TransporteHTTP
from protocolo.transporte_stdio import ErrorTransporte, TransporteStdio

# Separador utilizado para prefijar el nombre de la herramienta con la clave del servidor
SEPARADOR = "__"

# Expresion que valida los caracteres admitidos por la API en el nombre de una herramienta
PATRON_NOMBRE = re.compile(r"[^a-zA-Z0-9_-]")


class AdministradorMCP:
    """Administra el conjunto de clientes MCP disponibles para el anfitrion."""

    def __init__(self, log, ruta_configuracion=None):
        self.log = log
        self.ruta = Path(ruta_configuracion or configuracion.ARCHIVO_SERVIDORES)
        self.definiciones = {}
        self.clientes = {}
        self.mapa_herramientas = {}
        self.cargar_definiciones()

    def _sustituir(self, valor):
        """Reemplaza los marcadores de configuracion por sus valores reales."""
        if not isinstance(valor, str):
            return valor
        reemplazos = {
            "{RAIZ}": str(configuracion.RAIZ),
            "{ESPACIO_TRABAJO}": str(configuracion.ESPACIO_TRABAJO),
            "{PYTHON}": configuracion.INTERPRETE_PYTHON,
            "{URL_MCP_REMOTO}": configuracion.URL_MCP_REMOTO,
        }
        for marcador, contenido in reemplazos.items():
            valor = valor.replace(marcador, contenido)
        return valor

    def cargar_definiciones(self):
        """Lee el archivo servidores.json y guarda la definicion de cada servidor."""
        self.definiciones = {}
        if not self.ruta.exists():
            return self.definiciones
        with self.ruta.open("r", encoding="utf-8") as manejador:
            datos = json.load(manejador)
        for definicion in datos.get("servidores", []):
            clave = definicion.get("clave")
            if clave:
                self.definiciones[clave] = definicion
        return self.definiciones

    def _construir_transporte(self, definicion):
        """Crea el transporte adecuado segun el tipo declarado para el servidor."""
        tipo = definicion.get("tipo", "stdio")
        if tipo == "stdio":
            comando = self._sustituir(definicion.get("comando", ""))
            argumentos = [self._sustituir(argumento) for argumento in definicion.get("argumentos", [])]
            entorno = {clave: self._sustituir(valor) for clave, valor in (definicion.get("entorno") or {}).items()}
            return TransporteStdio(
                comando,
                argumentos,
                directorio=str(configuracion.RAIZ),
                entorno=entorno,
                tiempo_espera=configuracion.TIEMPO_ESPERA_MCP,
            )
        if tipo == "http":
            url = self._sustituir(definicion.get("url", ""))
            encabezados = {clave: self._sustituir(valor) for clave, valor in (definicion.get("encabezados") or {}).items()}
            return TransporteHTTP(
                url,
                encabezados=encabezados,
                tiempo_espera=configuracion.TIEMPO_ESPERA_MCP,
                version_protocolo=configuracion.VERSION_PROTOCOLO,
            )
        raise ErrorTransporte(f"el tipo de transporte {tipo} no esta soportado")

    def conectar(self, clave):
        """Conecta un servidor especifico y registra su cliente."""
        if clave in self.clientes:
            return self.clientes[clave]
        definicion = self.definiciones.get(clave)
        if definicion is None:
            raise ErrorTransporte(f"no existe la definicion del servidor {clave}")
        transporte = self._construir_transporte(definicion)
        cliente = ClienteMCP(
            clave,
            definicion.get("nombre", clave),
            transporte,
            self.log,
            configuracion.VERSION_PROTOCOLO,
            configuracion.NOMBRE_CLIENTE,
            configuracion.VERSION_CLIENTE,
        )
        try:
            cliente.conectar()
        except Exception as detalle:
            # La salida de error del servidor suele contener el motivo real de la falla
            diagnostico = []
            try:
                diagnostico = transporte.diagnostico(6)
            except Exception:
                diagnostico = []
            cliente.desconectar()
            texto = str(detalle)
            for linea in diagnostico:
                if linea not in texto:
                    texto += "\n" + linea
            raise ErrorTransporte(texto)
        self.clientes[clave] = cliente
        self._reconstruir_mapa()
        return cliente

    def conectar_habilitados(self):
        """Conecta todos los servidores marcados como habilitados en la configuracion."""
        resultados = []
        for clave, definicion in self.definiciones.items():
            if not definicion.get("habilitado", False):
                continue
            try:
                cliente = self.conectar(clave)
                resultados.append((clave, True, f"{len(cliente.herramientas)} herramientas disponibles"))
            except Exception as detalle:
                resultados.append((clave, False, str(detalle)))
        return resultados

    def desconectar(self, clave):
        """Cierra la conexion con un servidor especifico."""
        cliente = self.clientes.pop(clave, None)
        if cliente is None:
            return False
        cliente.desconectar()
        self._reconstruir_mapa()
        return True

    def desconectar_todos(self):
        """Cierra la conexion con todos los servidores activos."""
        for clave in list(self.clientes.keys()):
            self.desconectar(clave)

    def _normalizar(self, texto):
        """Ajusta un nombre para que cumpla con los caracteres admitidos por la API."""
        return PATRON_NOMBRE.sub("_", texto)

    def _reconstruir_mapa(self):
        """Recalcula la correspondencia entre el nombre expuesto al modelo y la herramienta real."""
        self.mapa_herramientas = {}
        for clave, cliente in self.clientes.items():
            for herramienta in cliente.herramientas:
                nombre_real = herramienta.get("name", "")
                nombre_expuesto = self._normalizar(f"{clave}{SEPARADOR}{nombre_real}")[:64]
                self.mapa_herramientas[nombre_expuesto] = (clave, nombre_real, herramienta)

    def herramientas_para_llm(self):
        """Devuelve el catalogo consolidado con el formato que exige la API del modelo."""
        catalogo = []
        for nombre_expuesto, (clave, nombre_real, herramienta) in self.mapa_herramientas.items():
            definicion = self.definiciones.get(clave, {})
            descripcion = herramienta.get("description", "") or f"Herramienta {nombre_real}"
            catalogo.append(
                {
                    "name": nombre_expuesto,
                    "description": f"[{definicion.get('nombre', clave)}] {descripcion}"[:1000],
                    "input_schema": herramienta.get("inputSchema") or {"type": "object", "properties": {}},
                }
            )
        return catalogo

    def catalogo_detallado(self):
        """Devuelve el catalogo de herramientas organizado por servidor para mostrarlo en pantalla."""
        detalle = []
        for clave, cliente in self.clientes.items():
            herramientas = []
            for herramienta in cliente.herramientas:
                herramientas.append(
                    {
                        "nombre": herramienta.get("name", ""),
                        "expuesto": self._normalizar(f"{clave}{SEPARADOR}{herramienta.get('name', '')}")[:64],
                        "descripcion": herramienta.get("description", ""),
                        "parametros": list((herramienta.get("inputSchema") or {}).get("properties", {}).keys()),
                        "requeridos": (herramienta.get("inputSchema") or {}).get("required", []),
                    }
                )
            detalle.append(
                {
                    "clave": clave,
                    "nombre": cliente.nombre,
                    "transporte": cliente.transporte.tipo,
                    "destino": cliente.transporte.descripcion(),
                    "servidor": cliente.informacion_servidor,
                    "version": getattr(cliente, "version_negociada", ""),
                    "herramientas": herramientas,
                }
            )
        return detalle

    def resolver(self, nombre_expuesto):
        """Traduce el nombre recibido del modelo hacia el servidor y la herramienta reales."""
        return self.mapa_herramientas.get(nombre_expuesto)

    def _extraer_texto(self, resultado):
        """Convierte el contenido devuelto por tools/call en un texto plano."""
        partes = []
        for bloque in resultado.get("content", []):
            tipo = bloque.get("type")
            if tipo == "text":
                partes.append(bloque.get("text", ""))
            elif tipo == "resource":
                recurso = bloque.get("resource", {})
                partes.append(recurso.get("text", json.dumps(recurso, ensure_ascii=False)))
            else:
                partes.append(json.dumps(bloque, ensure_ascii=False))
        if not partes and "structuredContent" in resultado:
            partes.append(json.dumps(resultado["structuredContent"], ensure_ascii=False))
        return "\n".join(partes) if partes else "la herramienta no devolvio contenido"

    def ejecutar(self, nombre_expuesto, argumentos):
        """Invoca la herramienta solicitada y devuelve el texto del resultado junto con la bandera de error."""
        destino = self.resolver(nombre_expuesto)
        if destino is None:
            return f"la herramienta {nombre_expuesto} no esta disponible en los servidores conectados", True
        clave, nombre_real, _ = destino
        cliente = self.clientes.get(clave)
        if cliente is None:
            return f"el servidor {clave} no esta conectado", True
        try:
            resultado = cliente.llamar_herramienta(nombre_real, argumentos)
        except Exception as detalle:
            return f"falla al invocar {nombre_real} en {clave}: {detalle}", True
        return self._extraer_texto(resultado), bool(resultado.get("isError", False))

    def estado(self):
        """Devuelve el estado de todos los servidores definidos en la configuracion."""
        filas = []
        for clave, definicion in self.definiciones.items():
            cliente = self.clientes.get(clave)
            if definicion.get("tipo") == "http":
                destino = self._sustituir(definicion.get("url", ""))
            else:
                destino = " ".join(
                    [self._sustituir(definicion.get("comando", ""))]
                    + [self._sustituir(argumento) for argumento in definicion.get("argumentos", [])]
                )
            filas.append(
                {
                    "clave": clave,
                    "nombre": definicion.get("nombre", clave),
                    "tipo": definicion.get("tipo", "stdio"),
                    "habilitado": definicion.get("habilitado", False),
                    "conectado": cliente is not None,
                    "herramientas": len(cliente.herramientas) if cliente else 0,
                    # Un destino vacio indica que falta completar la direccion en el archivo .env
                    "destino": destino.strip() or "sin configurar, define URL_MCP_REMOTO en el archivo .env",
                }
            )
        return filas
