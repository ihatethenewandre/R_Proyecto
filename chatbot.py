"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
chatbot.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Modulo que implementa el anfitrion del sistema, es decir, el chatbot que coordina al modelo de lenguaje y
             a los clientes MCP.

             Mantiene el historial completo de la conversacion para conservar el contexto dentro de la sesion, entrega
             al modelo el catalogo consolidado de herramientas, ejecuta los ciclos de invocacion cuando el modelo
             decide usar una herramienta, devuelve los resultados en bloques tool_result y consolida la respuesta final
             que se presenta al usuario. Tambien expone utilidades para reiniciar el contexto y consultar su tamaño.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import json

from llm.cliente_anthropic import ErrorLLM


class Chatbot:
    """Anfitrion que integra el modelo de lenguaje con los servidores MCP conectados."""

    def __init__(self, cliente_llm, administrador, mensaje_sistema, max_iteraciones=8):
        self.llm = cliente_llm
        self.administrador = administrador
        self.mensaje_sistema = mensaje_sistema
        self.max_iteraciones = max_iteraciones
        self.mensajes = []
        self.tokens_entrada = 0
        self.tokens_salida = 0

    def reiniciar(self):
        """Elimina el historial de la conversacion y con ello el contexto acumulado."""
        self.mensajes = []
        self.tokens_entrada = 0
        self.tokens_salida = 0

    def turnos(self):
        """Devuelve la cantidad de mensajes almacenados en el contexto."""
        return len(self.mensajes)

    def _acumular_uso(self, respuesta):
        """Suma el consumo de tokens reportado por la API."""
        uso = respuesta.get("usage", {})
        self.tokens_entrada += uso.get("input_tokens", 0)
        self.tokens_salida += uso.get("output_tokens", 0)

    def responder(self, entrada, al_invocar=None, al_resultado=None, al_texto=None):
        """Procesa una consulta del usuario y devuelve la respuesta final del anfitrion."""
        # El mensaje del usuario se agrega al historial para conservar el contexto
        self.mensajes.append({"role": "user", "content": entrada})
        herramientas = self.administrador.herramientas_para_llm()
        respuestas = []

        for _ in range(self.max_iteraciones):
            try:
                respuesta = self.llm.enviar(self.mensajes, herramientas, self.mensaje_sistema)
            except ErrorLLM:
                # El mensaje del usuario se retira para no dejar el historial en un estado inconsistente
                self.mensajes.pop()
                raise

            self._acumular_uso(respuesta)
            contenido = respuesta.get("content", [])
            # La respuesta del modelo se agrega integra para que los bloques tool_use conserven su identificador
            self.mensajes.append({"role": "assistant", "content": contenido})

            texto = self.llm.extraer_texto(respuesta)
            if texto:
                respuestas.append(texto)
                if al_texto:
                    al_texto(texto)

            usos = self.llm.extraer_usos(respuesta)
            if respuesta.get("stop_reason") != "tool_use" or not usos:
                break

            resultados = []
            for uso in usos:
                nombre = uso.get("name", "")
                argumentos = uso.get("input", {}) or {}
                if al_invocar:
                    al_invocar(nombre, argumentos)
                salida, es_error = self.administrador.ejecutar(nombre, argumentos)
                if al_resultado:
                    al_resultado(nombre, salida, es_error)
                resultados.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": uso.get("id"),
                        "content": salida if isinstance(salida, str) else json.dumps(salida, ensure_ascii=False),
                        "is_error": es_error,
                    }
                )
            # Los resultados regresan al modelo dentro de un mensaje con rol de usuario
            self.mensajes.append({"role": "user", "content": resultados})

        if not respuestas:
            return "el modelo no genero una respuesta de texto para esta consulta"
        return "\n\n".join(respuestas)
