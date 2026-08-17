"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
main.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Programa principal del Proyecto 1, un chatbot de consola que actua como anfitrion de varios servidores.

             Presenta el encabezado institucional y el menu principal, administra la conexion con los servidores
             oficiales de Filesystem y Git y con el servidor propio de la cadena de farmacias, mantiene la conversacion
             con el modelo de lenguaje conservando el contexto de la sesion, permite invocar herramientas de forma
             directa sin intervencion del modelo y muestra la bitacora completa de solicitudes y respuestas del
             protocolo JSON-RPC.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import json
import sys

import bitacora as registro
import configuracion
import consola
from chatbot import Chatbot
from llm.cliente_anthropic import ClienteAnthropic, ErrorLLM
from protocolo.administrador import AdministradorMCP


def construir_entorno():
    """Prepara los directorios, la bitacora, el administrador de conexiones y el chatbot anfitrion."""
    configuracion.preparar_directorios()
    log = registro.Bitacora(configuracion.DIRECTORIO_BITACORA, consola.ANCHO)
    administrador = AdministradorMCP(log)
    cliente_llm = ClienteAnthropic(
        configuracion.ANTHROPIC_API_KEY,
        configuracion.MODELO_LLM,
        configuracion.URL_API_LLM,
        configuracion.VERSION_API_LLM,
        configuracion.MAX_TOKENS,
        configuracion.TEMPERATURA,
        configuracion.TIEMPO_ESPERA_LLM,
    )
    anfitrion = Chatbot(
        cliente_llm,
        administrador,
        configuracion.MENSAJE_SISTEMA,
        configuracion.MAX_ITERACIONES_HERRAMIENTAS,
    )
    return log, administrador, anfitrion


def imprimir_estado(administrador):
    """Muestra la tabla de estado de todos los servidores definidos."""
    consola.franja("Estado")
    encabezado = (
        f"{'CLAVE'.ljust(14)}{'TIPO'.ljust(8)}{'HABILITADO'.ljust(12)}"
        f"{'CONECTADO'.ljust(12)}{'HERRAMIENTAS'.ljust(14)}NOMBRE"
    )
    print(encabezado)
    for fila in administrador.estado():
        print(
            f"{fila['clave'].ljust(14)}"
            f"{fila['tipo'].ljust(8)}"
            f"{('si' if fila['habilitado'] else 'no').ljust(12)}"
            f"{('si' if fila['conectado'] else 'no').ljust(12)}"
            f"{str(fila['herramientas']).ljust(14)}"
            f"{fila['nombre']}"
        )
    consola.espacio()
    for fila in administrador.estado():
        consola.parrafo(f"{fila['clave']}: {consola.truncar(fila['destino'], 108)}")
    consola.espacio()


def imprimir_detalle(clave, estado, detalle):
    """Imprime el resultado de un intento de conexion, incluyendo el diagnostico del servidor."""
    lineas = [texto for texto in str(detalle).splitlines() if texto.strip()]
    primera = lineas[0] if lineas else ""
    consola.parrafo(f"{clave}: {estado}, {primera}")
    # Las lineas restantes son la salida de error del servidor y se muestran con sangria
    for linea in lineas[1:]:
        consola.parrafo(consola.truncar(linea, 112), sangria="    ")


def conectar_todos(administrador):
    """Conecta todos los servidores habilitados e informa el resultado de cada intento."""
    consola.franja("Conexion")
    resultados = administrador.conectar_habilitados()
    if not resultados:
        consola.parrafo("No hay servidores habilitados en el archivo de configuracion.")
        consola.espacio()
        return
    for clave, exito, detalle in resultados:
        imprimir_detalle(clave, "conectado" if exito else "no conectado", detalle)
    consola.espacio()


def menu_servidores(administrador):
    """Presenta el submenu de administracion de servidores."""
    while True:
        opcion = consola.menu(
            "Servidores",
            [
                "Conectar todos los servidores habilitados",
                "Conectar un servidor especifico",
                "Desconectar un servidor",
                "Mostrar el estado de los servidores",
                "Verificar la conexion con un Ping",
                "Volver",
            ],
        )
        if opcion == "1":
            conectar_todos(administrador)
        elif opcion == "2":
            imprimir_estado(administrador)
            clave = consola.leer("Ingresa la clave del servidor:")
            if not clave:
                continue
            try:
                cliente = administrador.conectar(clave)
                consola.parrafo(
                    f"Servidor {clave} conectado, expone {len(cliente.herramientas)} herramientas, "
                    f"version negociada {getattr(cliente, 'version_negociada', 'no reportada')}."
                )
                consola.espacio()
            except Exception as detalle:
                imprimir_detalle(clave, "no conectado", detalle)
                consola.espacio()
        elif opcion == "3":
            clave = consola.leer("Ingresa la clave del servidor a desconectar:")
            if administrador.desconectar(clave):
                consola.parrafo(f"El servidor {clave} fue desconectado.")
            else:
                consola.parrafo(f"El servidor {clave} no estaba conectado.")
            consola.espacio()
        elif opcion == "4":
            imprimir_estado(administrador)
        elif opcion == "5":
            clave = consola.leer("Ingresa la clave del servidor:")
            cliente = administrador.clientes.get(clave)
            if cliente is None:
                consola.error(f"el servidor {clave} no esta conectado")
                continue
            try:
                cliente.ping()
                consola.parrafo(f"El servidor {clave} respondio correctamente al Ping.")
                consola.espacio()
            except Exception as detalle:
                consola.error(str(detalle))
        elif opcion == "6":
            return
        else:
            consola.error("la opcion ingresada no es valida")


def menu_herramientas(administrador):
    """Muestra el catalogo de herramientas expuesto por los servidores conectados."""
    consola.franja("Herramientas")
    catalogo = administrador.catalogo_detallado()
    if not catalogo:
        consola.parrafo("No hay servidores conectados, conecta al menos uno desde el menu de servidores.")
        consola.espacio()
        return
    for servidor in catalogo:
        consola.campo("Servidor:", f"{servidor['nombre']} ({servidor['clave']})")
        consola.campo("Transporte:", servidor["transporte"])
        consola.campo("Destino:", consola.truncar(servidor["destino"], 90))
        consola.campo("Version negociada:", servidor["version"] or "no reportada")
        consola.campo(
            "Implementacion:",
            f"{servidor['servidor'].get('name', 'no reportada')} {servidor['servidor'].get('version', '')}".strip(),
        )
        consola.campo("Total de herramientas:", str(len(servidor["herramientas"])))
        consola.espacio()
        for herramienta in servidor["herramientas"]:
            print(f"{herramienta['nombre']}")
            consola.parrafo(consola.truncar(herramienta["descripcion"] or "sin descripcion", 116), sangria="    ")
            parametros = ", ".join(herramienta["parametros"]) if herramienta["parametros"] else "sin parametros"
            print(f"    parametros: {parametros}")
            if herramienta["requeridos"]:
                print(f"    obligatorios: {', '.join(herramienta['requeridos'])}")
            print(f"    nombre expuesto al modelo: {herramienta['expuesto']}")
            consola.espacio()


def menu_invocacion(administrador):
    """Permite invocar una herramienta sin intervencion del modelo de lenguaje."""
    while True:
        opcion = consola.menu(
            "Invocacion",
            [
                "Listar las herramientas disponibles",
                "Invocar una herramienta",
                "Verificar la conexion con un Ping",
                "Volver",
            ],
        )
        if opcion == "1":
            if not administrador.mapa_herramientas:
                consola.parrafo("No hay herramientas disponibles, conecta al menos un servidor.")
                consola.espacio()
                continue
            consola.franja("Disponibles")
            for nombre in sorted(administrador.mapa_herramientas):
                clave, real, _ = administrador.mapa_herramientas[nombre]
                print(f"{nombre.ljust(48)}servidor: {clave.ljust(14)}herramienta: {real}")
            consola.espacio()
        elif opcion == "2":
            nombre = consola.leer("Ingresa el nombre de la herramienta:")
            if not nombre:
                continue
            crudo = consola.leer("Ingresa los argumentos en formato JSON:")
            try:
                argumentos = json.loads(crudo) if crudo else {}
            except json.JSONDecodeError as detalle:
                consola.error(f"los argumentos no son un JSON valido: {detalle}")
                continue
            salida, es_error = administrador.ejecutar(nombre, argumentos)
            consola.franja("Resultado")
            consola.campo("Herramienta:", nombre)
            consola.campo("Estado:", "error" if es_error else "correcto")
            consola.espacio()
            print(salida)
            consola.espacio()
        elif opcion == "3":
            clave = consola.leer("Ingresa la clave del servidor:")
            cliente = administrador.clientes.get(clave)
            if cliente is None:
                consola.error(f"el servidor {clave} no esta conectado")
                continue
            try:
                cliente.ping()
                consola.parrafo(f"El servidor {clave} respondio correctamente al Ping.")
                consola.espacio()
            except Exception as detalle:
                consola.error(str(detalle))
        elif opcion == "4":
            return
        else:
            consola.error("la opcion ingresada no es valida")


def mostrar_registros(log, entradas, detallado):
    """Imprime un conjunto de entradas de la bitacora con el formato del proyecto."""
    consola.franja("Registro")
    if not entradas:
        consola.parrafo("No hay interacciones registradas en la sesion actual.")
        consola.espacio()
        return
    consola.campo("Archivo de la sesion:", str(log.archivo))
    consola.campo("Interacciones mostradas:", f"{len(entradas)} de {log.total()}")
    consola.espacio()
    for entrada in entradas:
        for linea in log.formatear(entrada, detallado):
            print(linea)
        if detallado:
            consola.espacio()
    if not detallado:
        consola.espacio()


def menu_bitacora(log):
    """Presenta el submenu de consulta de la bitacora de interacciones."""
    while True:
        opcion = consola.menu(
            "Bitacora",
            [
                "Mostrar las ultimas interacciones",
                "Mostrar todas las interacciones",
                "Mostrar solo el resumen sin el contenido de los mensajes",
                "Filtrar por servidor",
                "Exportar la bitacora a un archivo",
                "Volver",
            ],
        )
        if opcion == "1":
            crudo = consola.leer("Ingresa la cantidad de interacciones a mostrar:")
            try:
                cantidad = int(crudo)
            except ValueError:
                consola.error("la cantidad debe ser un numero entero")
                continue
            mostrar_registros(log, log.ultimos(cantidad), True)
        elif opcion == "2":
            mostrar_registros(log, log.registros, True)
        elif opcion == "3":
            mostrar_registros(log, log.registros, False)
        elif opcion == "4":
            clave = consola.leer("Ingresa la clave del servidor:")
            mostrar_registros(log, log.filtrar(servidor=clave), True)
        elif opcion == "5":
            destino = configuracion.DIRECTORIO_BITACORA / "bitacora_exportada.json"
            log.exportar(destino)
            consola.parrafo(f"La bitacora se exporto en {destino}")
            consola.espacio()
        elif opcion == "6":
            return
        else:
            consola.error("la opcion ingresada no es valida")


def menu_configuracion(anfitrion, log):
    """Muestra los parametros activos del anfitrion y el consumo de la sesion."""
    consola.franja("Configuracion")
    for etiqueta, valor in configuracion.resumen():
        consola.campo(f"{etiqueta}:", consola.truncar(valor, 90), 26)
    consola.espacio()
    consola.campo("Mensajes en contexto:", str(anfitrion.turnos()), 26)
    consola.campo("Tokens de entrada:", str(anfitrion.tokens_entrada), 26)
    consola.campo("Tokens de salida:", str(anfitrion.tokens_salida), 26)
    consola.campo("Eventos en bitacora:", str(log.total()), 26)
    consola.espacio()


def sesion_chat(anfitrion, administrador):
    """Ejecuta la sesion de conversacion con el modelo de lenguaje."""
    consola.franja("Chat")
    if not anfitrion.llm.disponible():
        consola.parrafo(
            "No se encontro la clave de la API. Copia el archivo .env.example como .env y define el valor de "
            "ANTHROPIC_API_KEY antes de iniciar una conversacion."
        )
        consola.espacio()
        return

    consola.parrafo(
        "Escribe tu consulta y presiona Enter. El anfitrion decidira cuando invocar las herramientas de los "
        "servidores conectados y mostrara cada invocacion antes de entregar la respuesta final."
    )
    consola.espacio()

    consola.franja("Comandos")
    print("Salir: regresa al menu principal")
    print("Limpiar: reinicia el contexto de la conversacion")
    print("Contexto: muestra la cantidad de mensajes almacenados")
    print("Herramientas: muestra la cantidad de herramientas disponibles")
    consola.espacio()

    def al_invocar(nombre, argumentos):
        """Informa al usuario que el modelo decidio invocar una herramienta."""
        print(f"Invocando herramienta: {nombre}")
        print(f"Argumentos: {consola.truncar(json.dumps(argumentos, ensure_ascii=False), 100)}")

    def al_resultado(nombre, salida, es_error):
        """Informa al usuario el resultado devuelto por la herramienta invocada."""
        estado = "error" if es_error else "correcto"
        print(f"Resultado de {nombre}: {estado}")
        print(f"Contenido: {consola.truncar(salida, 100)}")
        consola.espacio()

    while True:
        entrada = consola.leer_sin_espacio("Consulta:")
        consola.espacio()
        if not entrada:
            continue
        comando = entrada.lower()
        if comando == "salir":
            return
        if comando == "limpiar":
            anfitrion.reiniciar()
            consola.parrafo("El contexto de la conversacion fue reiniciado.")
            consola.espacio()
            continue
        if comando == "contexto":
            consola.parrafo(f"El contexto almacena {anfitrion.turnos()} mensajes de la sesion actual.")
            consola.espacio()
            continue
        if comando == "herramientas":
            consola.parrafo(
                f"Hay {len(administrador.mapa_herramientas)} herramientas disponibles en "
                f"{len(administrador.clientes)} servidores conectados."
            )
            consola.espacio()
            continue

        try:
            respuesta = anfitrion.responder(entrada, al_invocar=al_invocar, al_resultado=al_resultado)
        except ErrorLLM as detalle:
            consola.error(str(detalle))
            continue
        except Exception as detalle:
            consola.error(f"falla inesperada durante la conversacion: {detalle}")
            continue

        print("Respuesta:")
        consola.parrafo(respuesta)
        consola.espacio()


def main():
    """Punto de entrada del programa."""
    consola.encabezado()
    log, administrador, anfitrion = construir_entorno()

    while True:
        opcion = consola.menu(
            "Menu principal",
            [
                "Chat: inicia una conversacion con el modelo a traves de la consola",
                "Servidores: gestiona los servidores disponibles",
                "Herramientas: revisa las herramientas disponibles con los servidores actuales",
                "Invocacion: utiliza una herramienta directamente, sin el modelo",
                "Bitacora: consulta la bitacora de solicitudes y respuestas",
                "Configuracion: revisa los parametros de la sesion actual",
                "Salir",
            ],
        )

        if opcion == "1":
            sesion_chat(anfitrion, administrador)
        elif opcion == "2":
            menu_servidores(administrador)
        elif opcion == "3":
            menu_herramientas(administrador)
        elif opcion == "4":
            menu_invocacion(administrador)
        elif opcion == "5":
            menu_bitacora(log)
        elif opcion == "6":
            menu_configuracion(anfitrion, log)
        elif opcion == "7":
            consola.franja("Cierre")
            administrador.desconectar_todos()
            consola.campo("Eventos registrados:", str(log.total()))
            consola.campo("Archivo de la bitacora:", str(log.archivo))
            consola.espacio()
            consola.parrafo("Sesion finalizada.")
            consola.espacio()
            return
        else:
            consola.error("la opcion ingresada no es valida")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        consola.espacio()
        consola.parrafo("Ejecucion interrumpida por el usuario.")
        consola.espacio()
        sys.exit(0)
