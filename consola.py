"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
consola.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Modulo que centraliza el estilo de todas las salidas de texto del proyecto en la terminal.

             Define el ancho fijo de 120 caracteres, las lineas divisorias, las franjas divisorias con titulos centrados
             en mayusculas, el encabezado institucional, los menus numerados y las funciones de lectura de datos desde
             el teclado. Garantiza que siempre exista un espacio de separacion despues de que el usuario ingrese un
             valor y al finalizar cada bloque de salida.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import textwrap

# Ancho fijo utilizado por todas las lineas divisorias del proyecto
ANCHO = 120

# Datos institucionales que se muestran en el encabezado principal
UNIVERSIDAD = "UNIVERSIDAD DEL VALLE DE GUATEMALA"
FACULTAD = "Facultad de Ingenieria"
DEPARTAMENTO = "Departamento de Computacion"
CURSO = "Redes"
PROYECTO = "Proyecto 1"
AUTOR = "Andre Emilio Pivaral Lopez - 23574"


def linea():
    """Imprime una linea divisoria de 120 caracteres."""
    print("-" * ANCHO)


def espacio():
    """Imprime un salto de linea de separacion."""
    print()


def franja(titulo):
    """Imprime una franja divisoria con el titulo centrado y en mayusculas."""
    linea()
    print(titulo.upper().center(ANCHO))
    linea()


def encabezado():
    """Imprime el encabezado institucional del proyecto."""
    linea()
    print(UNIVERSIDAD.center(ANCHO))
    linea()
    print(FACULTAD)
    print(DEPARTAMENTO)
    print(CURSO)
    espacio()
    print(PROYECTO)
    print(AUTOR)
    espacio()


def parrafo(texto, sangria=""):
    """Imprime un parrafo ajustado al ancho de 120 caracteres."""
    for linea_ajustada in textwrap.wrap(texto, width=ANCHO, initial_indent=sangria, subsequent_indent=sangria):
        print(linea_ajustada)


def campo(etiqueta, valor, ancho_etiqueta=24):
    """Imprime un par de etiqueta y valor alineados en columnas."""
    print(f"{etiqueta.ljust(ancho_etiqueta)}{valor}")


def bloque(titulo, lineas):
    """Imprime una franja divisoria seguida de un conjunto de lineas de contenido."""
    franja(titulo)
    for elemento in lineas:
        print(elemento)
    espacio()


def menu(titulo, opciones, mensaje="Selecciona una Opcion:"):
    """Imprime un menu numerado y devuelve la opcion ingresada por el usuario."""
    franja(titulo)
    # Cada opcion se numera con el formato "N. " solicitado
    for indice, opcion in enumerate(opciones, start=1):
        print(f"{indice}. {opcion}")
    espacio()
    seleccion = input(f"{mensaje} ").strip()
    espacio()
    return seleccion


def leer(mensaje):
    """Lee una cadena desde el teclado y agrega el espacio de separacion posterior."""
    valor = input(f"{mensaje} ").strip()
    espacio()
    return valor


def leer_sin_espacio(mensaje):
    """Lee una cadena desde el teclado sin agregar el espacio de separacion posterior."""
    return input(f"{mensaje} ").strip()


def pausa():
    """Detiene la ejecucion hasta que el usuario presione la tecla Enter."""
    input("Presiona Enter para continuar: ")
    espacio()


def aviso(texto):
    """Imprime un mensaje informativo con el espacio de separacion posterior."""
    parrafo(texto)
    espacio()


def error(texto):
    """Imprime un mensaje de error con el prefijo correspondiente."""
    parrafo(f"Error: {texto}")
    espacio()


def truncar(texto, limite=100):
    """Recorta un texto largo para que no rompa el formato de la terminal."""
    plano = " ".join(str(texto).split())
    if len(plano) <= limite:
        return plano
    return plano[: limite - 3] + "..."
