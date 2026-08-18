# ----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Dockerfile
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------
# UNIVERSIDAD DEL VALLE DE GUATEMALA
# Redes
#
# Descripcion: Imagen del servidor MCP propio en su variante remota sobre Streamable HTTP.
#
#              Empaqueta el nucleo del protocolo, la logica de dominio y el servidor HTTP en una imagen basada en
#              Python. El puerto de escucha se toma de la variable de entorno PORT, tal como lo exige Cloud Run.
#
# Autor:         Andre Emilio Pivaral Lopez
# Fecha:         26 de Agosto de 2026
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------

FROM python:3.11-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Se copian unicamente los archivos del servidor
COPY dominio.py nucleo_mcp.py servidor_remoto.py ./

# La salida no se almacena en memoria intermedia para que el registro llegue en tiempo real
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

CMD ["python", "servidor_remoto.py"]
