"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
transporte_stdio.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Modulo que implementa el transporte stdio del protocolo MCP para servidores que se ejecutan de forma local.

             Levanta el servidor como un proceso hijo y realiza el intercambio de mensajes JSON-RPC delimitados por
             salto de linea sobre las tuberias de entrada y salida estandar. Un hilo dedicado consume la salida del
             proceso para evitar bloqueos y otro hilo recolecta la salida de error que los servidores utilizan como
             canal de registro. La correlacion entre solicitudes y respuestas se realiza por el identificador del
             mensaje.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path


class ErrorTransporte(Exception):
    """Excepcion que representa una falla en el canal de comunicacion."""


class TransporteStdio:
    """Canal de comunicacion con un servidor MCP local mediante entrada y salida estandar."""

    def __init__(self, comando, argumentos=None, directorio=None, entorno=None, tiempo_espera=90):
        self.comando = comando
        self.argumentos = list(argumentos or [])
        self.directorio = directorio
        self.entorno = entorno
        self.tiempo_espera = tiempo_espera
        self.proceso = None
        self.cola_salida = queue.Queue()
        self.errores = []
        self.tipo = "stdio"

    def descripcion(self):
        """Devuelve la linea de comando utilizada para levantar el servidor."""
        return " ".join([self.comando] + self.argumentos)

    def _resolver_comando(self, comando):
        """Busca la ruta real del ejecutable probando las extensiones que usa cada sistema operativo."""
        # Un comando indicado con ruta absoluta se utiliza tal cual
        if os.path.isabs(comando) and os.path.exists(comando):
            return comando
        # En Windows se buscan primero las extensiones ejecutables, porque junto a npx.cmd existe un archivo npx sin
        # extension que es un script de shell; ejecutarlo produce el error WinError 193
        if os.name == "nt":
            for sufijo in (".exe", ".cmd", ".bat", ".com"):
                ubicacion = shutil.which(comando + sufijo)
                if ubicacion:
                    return ubicacion
            # Tambien se revisa el entorno virtual activo, donde pip instala uv.exe y uvx.exe
            for carpeta in ("Scripts", "bin"):
                base = Path(sys.prefix) / carpeta
                for sufijo in (".exe", ".cmd", ".bat"):
                    candidato = base / (comando + sufijo)
                    if candidato.exists():
                        return str(candidato)
        ubicacion = shutil.which(comando)
        if ubicacion:
            return ubicacion
        # Como ultimo recurso se busca el archivo sin extension dentro del entorno virtual activo
        for carpeta in ("Scripts", "bin"):
            candidato = Path(sys.prefix) / carpeta / comando
            if candidato.exists():
                return str(candidato)
        return comando

    def _leer_salida(self):
        """Hilo que traslada cada linea de la salida estandar del servidor hacia la cola interna."""
        for linea in self.proceso.stdout:
            texto = linea.strip()
            if texto:
                self.cola_salida.put(texto)
        self.cola_salida.put(None)

    def _leer_errores(self):
        """Hilo que almacena la salida de error del servidor para su diagnostico posterior."""
        for linea in self.proceso.stderr:
            texto = linea.rstrip()
            if texto:
                self.errores.append(texto)
                # Se conserva solo un historial acotado de mensajes de diagnostico
                if len(self.errores) > 200:
                    self.errores.pop(0)

    def _lanzar(self, orden, entorno_final):
        """Crea el proceso hijo con las tuberias del transporte ya configuradas."""
        return subprocess.Popen(
            orden,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=self.directorio,
            env=entorno_final,
        )

    def iniciar(self):
        """Levanta el proceso del servidor y activa los hilos de lectura."""
        ejecutable = self._resolver_comando(self.comando)
        entorno_final = os.environ.copy()
        if self.entorno:
            entorno_final.update(self.entorno)
        try:
            self.proceso = self._lanzar([ejecutable] + self.argumentos, entorno_final)
        except FileNotFoundError:
            raise ErrorTransporte(
                f"no se encontro el ejecutable {self.comando}. Si es npx instala Node.js, si es uvx ejecuta "
                f"pip install uv dentro del entorno virtual, y en ambos casos vuelve a abrir la terminal"
            )
        except OSError as detalle:
            # El error 193 de Windows indica que el archivo encontrado no es un binario, ocurre con los lanzadores
            # de npm que se distribuyen tambien como script de shell sin extension; se reintenta a traves de cmd.exe
            if os.name == "nt" and getattr(detalle, "winerror", None) == 193:
                interprete = os.environ.get("COMSPEC", "cmd.exe")
                try:
                    self.proceso = self._lanzar([interprete, "/c", ejecutable] + self.argumentos, entorno_final)
                except OSError as segundo:
                    raise ErrorTransporte(
                        f"no fue posible iniciar {self.comando} ni siquiera a traves de cmd.exe: {segundo}"
                    )
            else:
                raise ErrorTransporte(f"no fue posible iniciar el proceso: {detalle}")

        threading.Thread(target=self._leer_salida, daemon=True).start()
        threading.Thread(target=self._leer_errores, daemon=True).start()

    def activo(self):
        """Indica si el proceso del servidor sigue en ejecucion."""
        return self.proceso is not None and self.proceso.poll() is None

    def enviar(self, mensaje):
        """Serializa un mensaje JSON-RPC y lo escribe en la entrada estandar del servidor."""
        if not self.activo():
            raise ErrorTransporte("el proceso del servidor no esta activo")
        try:
            self.proceso.stdin.write(json.dumps(mensaje, ensure_ascii=False) + "\n")
            self.proceso.stdin.flush()
        except (BrokenPipeError, OSError) as detalle:
            raise ErrorTransporte(f"no fue posible escribir en el servidor: {detalle}")

    def _recibir_mensaje(self, tiempo_espera):
        """Obtiene el siguiente mensaje JSON valido publicado por el servidor."""
        while True:
            try:
                linea = self.cola_salida.get(timeout=tiempo_espera)
            except queue.Empty:
                raise ErrorTransporte(f"el servidor no respondio en {tiempo_espera} segundos")
            if linea is None:
                # El proceso termino, su salida de error contiene el motivo real de la falla
                time.sleep(0.4)
                codigo = self.proceso.poll() if self.proceso else "desconocido"
                detalle = self.diagnostico(6)
                mensaje = f"el servidor termino de forma inesperada con codigo {codigo}"
                if detalle:
                    mensaje += "\n" + "\n".join(detalle)
                raise ErrorTransporte(mensaje)
            try:
                return json.loads(linea)
            except json.JSONDecodeError:
                # Las lineas que no son JSON se tratan como mensajes de diagnostico del servidor
                self.errores.append(linea)

    def solicitar(self, mensaje, tiempo_espera=None):
        """Envia una solicitud y espera la respuesta que corresponde a su identificador."""
        limite = tiempo_espera or self.tiempo_espera
        identificador = mensaje.get("id")
        self.enviar(mensaje)
        pendientes = []
        while True:
            recibido = self._recibir_mensaje(limite)
            if recibido.get("id") == identificador and ("result" in recibido or "error" in recibido):
                return recibido, pendientes
            # Los mensajes que el servidor envia por iniciativa propia se devuelven para su registro
            pendientes.append(recibido)

    def notificar(self, mensaje):
        """Envia una notificacion que no genera respuesta."""
        self.enviar(mensaje)

    def diagnostico(self, cantidad=10):
        """Devuelve las ultimas lineas emitidas por el servidor en su salida de error."""
        return self.errores[-cantidad:]

    def cerrar(self):
        """Cierra las tuberias y termina el proceso del servidor."""
        if self.proceso is None:
            return
        try:
            if self.proceso.stdin and not self.proceso.stdin.closed:
                self.proceso.stdin.close()
        except OSError:
            pass
        try:
            self.proceso.terminate()
            self.proceso.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            # Si el proceso no responde a la terminacion ordenada se fuerza su cierre
            try:
                self.proceso.kill()
            except OSError:
                pass
        self.proceso = None
