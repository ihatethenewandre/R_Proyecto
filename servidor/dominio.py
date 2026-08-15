"""
----------------------------------------------------------------------------------------------------------------------------------------------------------------
dominio.py
----------------------------------------------------------------------------------------------------------------------------------------------------------------
UNIVERSIDAD DEL VALLE DE GUATEMALA
Redes

Descripcion: Modulo que contiene la logica de negocio del servidor MCP propio, basado en el caso de uso a nivel de
             industria propuesto en el enunciado: una cadena de farmacias que ofrece un chatbot para atender clientes,
             orientarlos segun sus sintomas y permitirles comprar medicamentos.

             Administra el padron de clientes con sus alergias y condiciones cronicas, el catalogo de medicamentos
             diferenciando los de venta libre de los que exigen receta, el inventario por sucursal, la evaluacion de
             sintomas con clasificacion de urgencia, la verificacion de interacciones entre principios activos y el
             ciclo de vida de los pedidos. Las validaciones de seguridad farmaceutica se resuelven en este modulo:
             signos de alarma que exigen atencion profesional, restricciones por edad, bloqueo por alergias declaradas
             y prohibicion de despachar medicamentos de receta sin la receta vigente registrada.

Autor:         Andre Emilio Pivaral Lopez
Fecha:         26 de Agosto de 2026
----------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path

# Archivo donde se persisten los pedidos generados por el servidor
ARCHIVO_DATOS = Path(__file__).resolve().parent / "datos_farmacia.json"

# Candado que protege la escritura concurrente cuando el servidor atiende varias peticiones HTTP
CANDADO = threading.Lock()

# Aviso que acompaña toda orientacion clinica entregada por el servidor
AVISO_CLINICO = (
    "Esta orientacion es informativa y no sustituye la evaluacion de un medico o de un farmaceutico colegiado. "
    "Si los sintomas persisten mas de tres dias, empeoran o aparecen signos de alarma, se debe acudir a consulta."
)

# Sucursales de la cadena de farmacias
SUCURSALES = {
    "SUC-01": {
        "codigo": "SUC-01",
        "nombre": "Sucursal Centro",
        "municipio": "Guatemala",
        "direccion": "8a Avenida 12-45, Zona 1",
        "horario": "lunes a domingo de 07:00 a 21:00",
        "servicio_domicilio": True,
        "farmaceutico_turno": True,
    },
    "SUC-02": {
        "codigo": "SUC-02",
        "nombre": "Sucursal Zona 10",
        "municipio": "Guatemala",
        "direccion": "5a Avenida 14-20, Zona 10",
        "horario": "lunes a domingo de 06:00 a 23:00",
        "servicio_domicilio": True,
        "farmaceutico_turno": True,
    },
    "SUC-03": {
        "codigo": "SUC-03",
        "nombre": "Sucursal Mixco",
        "municipio": "Mixco",
        "direccion": "Calzada San Juan 3-15, Zona 7",
        "horario": "lunes a sabado de 08:00 a 20:00",
        "servicio_domicilio": True,
        "farmaceutico_turno": False,
    },
    "SUC-04": {
        "codigo": "SUC-04",
        "nombre": "Sucursal Villa Nueva",
        "municipio": "Villa Nueva",
        "direccion": "Boulevard Principal 9-80, Zona 4",
        "horario": "lunes a sabado de 08:00 a 19:00",
        "servicio_domicilio": False,
        "farmaceutico_turno": False,
    },
}

# Catalogo de medicamentos identificados por su principio activo, sin nombres comerciales
MEDICAMENTOS = {
    "MED-1001": {
        "codigo": "MED-1001",
        "principio_activo": "acetaminofen",
        "presentacion": "tabletas de 500 mg, caja con 20 unidades",
        "categoria": "analgesico y antipiretico",
        "requiere_receta": False,
        "precio": 18.50,
        "edad_minima": 12,
        "indicaciones": "dolor leve a moderado y fiebre",
        "advertencias": "no exceder cuatro tomas al dia ni combinar con otros productos que contengan acetaminofen",
    },
    "MED-1002": {
        "codigo": "MED-1002",
        "principio_activo": "ibuprofeno",
        "presentacion": "tabletas de 400 mg, caja con 10 unidades",
        "categoria": "antiinflamatorio no esteroideo",
        "requiere_receta": False,
        "precio": 24.00,
        "edad_minima": 12,
        "indicaciones": "dolor con componente inflamatorio, dolor muscular y fiebre",
        "advertencias": "tomar con alimentos, no recomendado en gastritis, ulcera o enfermedad renal",
    },
    "MED-1003": {
        "codigo": "MED-1003",
        "principio_activo": "loratadina",
        "presentacion": "tabletas de 10 mg, caja con 10 unidades",
        "categoria": "antihistaminico",
        "requiere_receta": False,
        "precio": 32.00,
        "edad_minima": 6,
        "indicaciones": "rinitis alergica, estornudos, picazon nasal y ocular",
        "advertencias": "una toma cada 24 horas, puede causar somnolencia leve",
    },
    "MED-1004": {
        "codigo": "MED-1004",
        "principio_activo": "omeprazol",
        "presentacion": "capsulas de 20 mg, caja con 14 unidades",
        "categoria": "inhibidor de la bomba de protones",
        "requiere_receta": False,
        "precio": 45.00,
        "edad_minima": 18,
        "indicaciones": "acidez estomacal y reflujo",
        "advertencias": "tomar en ayunas, no usar por mas de 14 dias sin evaluacion medica",
    },
    "MED-1005": {
        "codigo": "MED-1005",
        "principio_activo": "sales de rehidratacion oral",
        "presentacion": "sobres de 20.5 g, caja con 6 unidades",
        "categoria": "rehidratante",
        "requiere_receta": False,
        "precio": 9.00,
        "edad_minima": 0,
        "indicaciones": "reposicion de liquidos y electrolitos en diarrea o vomito",
        "advertencias": "disolver un sobre en un litro de agua potable y consumir dentro de las 24 horas",
    },
    "MED-1006": {
        "codigo": "MED-1006",
        "principio_activo": "ambroxol",
        "presentacion": "jarabe de 120 ml",
        "categoria": "mucolitico y expectorante",
        "requiere_receta": False,
        "precio": 38.00,
        "edad_minima": 2,
        "indicaciones": "tos con flema y congestion bronquial",
        "advertencias": "no combinar con antitusivos que supriman el reflejo de la tos",
    },
    "MED-1007": {
        "codigo": "MED-1007",
        "principio_activo": "solucion salina nasal",
        "presentacion": "atomizador de 30 ml",
        "categoria": "descongestionante mecanico",
        "requiere_receta": False,
        "precio": 22.00,
        "edad_minima": 0,
        "indicaciones": "congestion nasal y limpieza de fosas nasales",
        "advertencias": "es de uso individual, no se debe compartir el atomizador",
    },
    "MED-1008": {
        "codigo": "MED-1008",
        "principio_activo": "naproxeno",
        "presentacion": "tabletas de 250 mg, caja con 10 unidades",
        "categoria": "antiinflamatorio no esteroideo",
        "requiere_receta": False,
        "precio": 28.00,
        "edad_minima": 12,
        "indicaciones": "dolor musculoesqueletico y colico menstrual",
        "advertencias": "tomar con alimentos, evitar el uso simultaneo con otros antiinflamatorios",
    },
    "MED-2001": {
        "codigo": "MED-2001",
        "principio_activo": "amoxicilina",
        "presentacion": "capsulas de 500 mg, caja con 21 unidades",
        "categoria": "antibiotico betalactamico",
        "requiere_receta": True,
        "precio": 65.00,
        "edad_minima": 12,
        "indicaciones": "infecciones bacterianas diagnosticadas por un medico",
        "advertencias": "completar el esquema indicado, contraindicado en alergia a la penicilina",
    },
    "MED-2002": {
        "codigo": "MED-2002",
        "principio_activo": "salbutamol",
        "presentacion": "inhalador de 100 mcg por disparo",
        "categoria": "broncodilatador",
        "requiere_receta": True,
        "precio": 95.00,
        "edad_minima": 4,
        "indicaciones": "crisis de broncoespasmo en pacientes con diagnostico previo",
        "advertencias": "si se requiere mas de dos veces por semana se debe reevaluar el tratamiento de fondo",
    },
    "MED-2003": {
        "codigo": "MED-2003",
        "principio_activo": "losartan",
        "presentacion": "tabletas de 50 mg, caja con 30 unidades",
        "categoria": "antihipertensivo",
        "requiere_receta": True,
        "precio": 78.00,
        "edad_minima": 18,
        "indicaciones": "control de la presion arterial bajo supervision medica",
        "advertencias": "no suspender el tratamiento sin indicacion medica",
    },
    "MED-2004": {
        "codigo": "MED-2004",
        "principio_activo": "metformina",
        "presentacion": "tabletas de 850 mg, caja con 30 unidades",
        "categoria": "antidiabetico oral",
        "requiere_receta": True,
        "precio": 52.00,
        "edad_minima": 18,
        "indicaciones": "control de la glucosa en diabetes tipo 2 diagnosticada",
        "advertencias": "tomar con alimentos, requiere control periodico de la funcion renal",
    },
}

# Existencias disponibles por sucursal
INVENTARIO = {
    "SUC-01": {"MED-1001": 40, "MED-1002": 25, "MED-1003": 18, "MED-1004": 12, "MED-1005": 60, "MED-1006": 15,
               "MED-1007": 22, "MED-1008": 10, "MED-2001": 8, "MED-2002": 5, "MED-2003": 14, "MED-2004": 16},
    "SUC-02": {"MED-1001": 55, "MED-1002": 30, "MED-1003": 24, "MED-1004": 20, "MED-1005": 45, "MED-1006": 12,
               "MED-1007": 30, "MED-1008": 16, "MED-2001": 12, "MED-2002": 9, "MED-2003": 20, "MED-2004": 22},
    "SUC-03": {"MED-1001": 20, "MED-1002": 8, "MED-1003": 6, "MED-1004": 4, "MED-1005": 25, "MED-1006": 5,
               "MED-1007": 9, "MED-1008": 0, "MED-2001": 3, "MED-2002": 0, "MED-2003": 6, "MED-2004": 7},
    "SUC-04": {"MED-1001": 12, "MED-1002": 4, "MED-1003": 3, "MED-1004": 0, "MED-1005": 18, "MED-1006": 2,
               "MED-1007": 5, "MED-1008": 2, "MED-2001": 0, "MED-2002": 0, "MED-2003": 2, "MED-2004": 3},
}

# Padron de clientes con sus alergias declaradas y condiciones cronicas
CLIENTES = {
    "CLI-1001": {
        "codigo": "CLI-1001",
        "nombre": "Maria Fernanda Ruiz",
        "edad": 34,
        "municipio": "Guatemala",
        "sucursal_preferida": "SUC-02",
        "alergias": ["penicilina"],
        "condiciones": [],
        "receta_vigente": [],
    },
    "CLI-1002": {
        "codigo": "CLI-1002",
        "nombre": "Carlos Estuardo Lima",
        "edad": 61,
        "municipio": "Mixco",
        "sucursal_preferida": "SUC-03",
        "alergias": [],
        "condiciones": ["hipertension", "gastritis"],
        "receta_vigente": ["MED-2003"],
    },
    "CLI-1003": {
        "codigo": "CLI-1003",
        "nombre": "Ana Lucia Morales",
        "edad": 27,
        "municipio": "Guatemala",
        "sucursal_preferida": "SUC-01",
        "alergias": ["antiinflamatorios no esteroideos"],
        "condiciones": ["rinitis alergica"],
        "receta_vigente": [],
    },
    "CLI-1004": {
        "codigo": "CLI-1004",
        "nombre": "Diego Alejandro Perez",
        "edad": 8,
        "municipio": "Villa Nueva",
        "sucursal_preferida": "SUC-04",
        "alergias": [],
        "condiciones": ["asma"],
        "receta_vigente": ["MED-2002"],
    },
    "CLI-1005": {
        "codigo": "CLI-1005",
        "nombre": "Rosa Elena Chavez",
        "edad": 52,
        "municipio": "Guatemala",
        "sucursal_preferida": "SUC-02",
        "alergias": ["sulfas"],
        "condiciones": ["diabetes tipo 2"],
        "receta_vigente": ["MED-2004"],
    },
}

# Correspondencia entre las alergias declaradas y los principios activos que deben bloquearse
BLOQUEO_POR_ALERGIA = {
    "penicilina": ["amoxicilina"],
    "antiinflamatorios no esteroideos": ["ibuprofeno", "naproxeno"],
    "aines": ["ibuprofeno", "naproxeno"],
    "sulfas": [],
}

# Sintomas de consulta frecuente y los productos de venta libre asociados
SINTOMAS = {
    "dolor de cabeza": {"medicamentos": ["MED-1001", "MED-1002"], "nota": "mantener hidratacion y descanso"},
    "fiebre": {"medicamentos": ["MED-1001"], "nota": "medir la temperatura cada cuatro horas y mantener hidratacion"},
    "dolor muscular": {"medicamentos": ["MED-1008", "MED-1002"], "nota": "aplicar reposo relativo sobre la zona afectada"},
    "dolor de garganta": {"medicamentos": ["MED-1001"], "nota": "consumir liquidos tibios y evitar irritantes"},
    "tos con flema": {"medicamentos": ["MED-1006"], "nota": "aumentar la ingesta de liquidos"},
    "congestion nasal": {"medicamentos": ["MED-1007", "MED-1003"], "nota": "realizar lavado nasal dos veces al dia"},
    "estornudos y picazon": {"medicamentos": ["MED-1003"], "nota": "identificar y evitar el alergeno desencadenante"},
    "acidez estomacal": {"medicamentos": ["MED-1004"], "nota": "evitar comidas irritantes y no acostarse despues de comer"},
    "diarrea": {"medicamentos": ["MED-1005"], "nota": "reponer liquidos despues de cada evacuacion"},
    "colico menstrual": {"medicamentos": ["MED-1008", "MED-1002"], "nota": "aplicar calor local sobre el abdomen"},
}

# Signos de alarma que obligan a suspender la recomendacion y derivar a atencion profesional
SINTOMAS_ALERTA = [
    "dolor en el pecho",
    "dificultad para respirar",
    "perdida de conciencia",
    "convulsiones",
    "sangrado abundante",
    "vomito con sangre",
    "entumecimiento de un lado del cuerpo",
    "dificultad para hablar",
    "vision borrosa repentina",
    "dolor abdominal intenso",
    "fiebre que no cede en 72 horas",
    "rigidez de cuello",
]

# Interacciones documentadas entre los principios activos del catalogo
INTERACCIONES = [
    {
        "principios": ["ibuprofeno", "naproxeno"],
        "severidad": "alta",
        "efecto": "duplicidad terapeutica de antiinflamatorios, aumenta el riesgo de sangrado y de daño gastrico",
    },
    {
        "principios": ["ibuprofeno", "losartan"],
        "severidad": "moderada",
        "efecto": "el antiinflamatorio reduce el efecto antihipertensivo y puede afectar la funcion renal",
    },
    {
        "principios": ["naproxeno", "losartan"],
        "severidad": "moderada",
        "efecto": "el antiinflamatorio reduce el efecto antihipertensivo y puede afectar la funcion renal",
    },
    {
        "principios": ["acetaminofen", "ibuprofeno"],
        "severidad": "baja",
        "efecto": "pueden alternarse bajo indicacion profesional, no deben tomarse juntos de forma rutinaria",
    },
    {
        "principios": ["omeprazol", "metformina"],
        "severidad": "baja",
        "efecto": "el uso prolongado del inhibidor puede reducir la absorcion de vitamina B12, requiere control",
    },
]

# Estados validos del ciclo de vida de un pedido
ESTADOS_PEDIDO = ["registrado", "en preparacion", "listo para retiro", "en ruta", "entregado", "anulado"]

# Modalidades de entrega admitidas
TIPOS_ENTREGA = ["retiro en sucursal", "entrega a domicilio"]


class ErrorDominio(Exception):
    """Excepcion que representa una violacion de las reglas de negocio."""


def _cargar():
    """Lee el archivo de persistencia y devuelve su contenido."""
    if not ARCHIVO_DATOS.exists():
        return {"consecutivo": 0, "pedidos": {}}
    try:
        with ARCHIVO_DATOS.open("r", encoding="utf-8") as manejador:
            return json.load(manejador)
    except (json.JSONDecodeError, OSError):
        return {"consecutivo": 0, "pedidos": {}}


def _guardar(datos):
    """Escribe el contenido actualizado en el archivo de persistencia."""
    try:
        with ARCHIVO_DATOS.open("w", encoding="utf-8") as manejador:
            json.dump(datos, manejador, ensure_ascii=False, indent=2)
    except OSError:
        # En entornos de solo lectura como algunos contenedores la persistencia es opcional
        pass


# Equivalencias que permiten comparar texto ingresado con o sin tildes
EQUIVALENCIAS = str.maketrans({
    "a": "a", "e": "e", "i": "i", "o": "o", "u": "u",
    "\u00e1": "a", "\u00e9": "e", "\u00ed": "i", "\u00f3": "o", "\u00fa": "u", "\u00fc": "u",
    "\u00c1": "a", "\u00c9": "e", "\u00cd": "i", "\u00d3": "o", "\u00da": "u",
})


def _normalizar(texto):
    """Deja un texto en minusculas, sin tildes y sin espacios sobrantes para poder compararlo."""
    return " ".join(str(texto).strip().lower().translate(EQUIVALENCIAS).split())


def _principios_bloqueados(alergias):
    """Devuelve los principios activos que deben bloquearse segun las alergias declaradas."""
    bloqueados = set()
    for alergia in alergias or []:
        clave = _normalizar(alergia)
        bloqueados.update(BLOQUEO_POR_ALERGIA.get(clave, []))
        # Una alergia declarada directamente sobre un principio activo tambien lo bloquea
        for medicamento in MEDICAMENTOS.values():
            if clave == medicamento["principio_activo"]:
                bloqueados.add(medicamento["principio_activo"])
    return bloqueados


def consultar_cliente(codigo_cliente):
    """Devuelve la ficha de un cliente con sus alergias, condiciones y sucursal preferida."""
    codigo = str(codigo_cliente).strip().upper()
    cliente = CLIENTES.get(codigo)
    if cliente is None:
        raise ErrorDominio(f"no existe el cliente {codigo}, los codigos validos tienen el formato CLI-1001")
    ficha = dict(cliente)
    ficha["sucursal"] = SUCURSALES.get(cliente["sucursal_preferida"], {})
    ficha["pedidos_activos"] = len(
        [p for p in listar_pedidos(codigo_cliente=codigo)["pedidos"] if p["estado"] not in ("entregado", "anulado")]
    )
    ficha["principios_bloqueados"] = sorted(_principios_bloqueados(cliente["alergias"]))
    return ficha


def listar_sucursales(municipio=None, servicio_domicilio=None):
    """Devuelve las sucursales de la cadena filtradas por municipio o por servicio a domicilio."""
    resultado = []
    for sucursal in SUCURSALES.values():
        if municipio and _normalizar(sucursal["municipio"]) != _normalizar(municipio):
            continue
        if servicio_domicilio is not None and sucursal["servicio_domicilio"] != bool(servicio_domicilio):
            continue
        resultado.append(sucursal)
    return {"total": len(resultado), "sucursales": resultado}


def buscar_medicamento(termino=None, solo_venta_libre=None, categoria=None):
    """Busca medicamentos por principio activo, categoria o indicacion."""
    consulta = _normalizar(termino) if termino else ""
    resultado = []
    for medicamento in MEDICAMENTOS.values():
        # El filtro de venta libre descarta los productos que exigen receta
        if solo_venta_libre is not None and bool(solo_venta_libre) and medicamento["requiere_receta"]:
            continue
        if categoria and _normalizar(categoria) not in _normalizar(medicamento["categoria"]):
            continue
        if consulta:
            campos = " ".join(
                [medicamento["principio_activo"], medicamento["categoria"], medicamento["indicaciones"], medicamento["codigo"]]
            )
            if consulta not in _normalizar(campos):
                continue
        resultado.append(medicamento)
    resultado.sort(key=lambda elemento: elemento["principio_activo"])
    return {"total": len(resultado), "medicamentos": resultado}


def evaluar_sintomas(sintomas, edad=None, alergias=None):
    """Clasifica la urgencia de un cuadro de sintomas y sugiere productos de venta libre cuando corresponde."""
    lista = [_normalizar(sintoma) for sintoma in (sintomas or []) if str(sintoma).strip()]
    if not lista:
        raise ErrorDominio("se debe indicar al menos un sintoma para poder orientar al cliente")

    # Los signos de alarma tienen prioridad absoluta sobre cualquier sugerencia de producto
    alertas = []
    for sintoma in lista:
        for alerta in SINTOMAS_ALERTA:
            if alerta in sintoma or sintoma in alerta:
                alertas.append(alerta)
    if alertas:
        return {
            "urgencia": "atencion inmediata",
            "sintomas_evaluados": lista,
            "signos_de_alarma": sorted(set(alertas)),
            "recomendacion": (
                "el cuadro descrito corresponde a un signo de alarma, se debe acudir de inmediato a un servicio de "
                "emergencia o comunicarse con el sistema de emergencias local, no se sugiere ningun medicamento"
            ),
            "sugerencias": [],
            "aviso": AVISO_CLINICO,
        }

    # En pacientes pediatricos la dosificacion depende del peso, por lo que se deriva al profesional
    if edad is not None and int(edad) < 12:
        return {
            "urgencia": "consulta profesional",
            "sintomas_evaluados": lista,
            "signos_de_alarma": [],
            "recomendacion": (
                "en menores de 12 años la dosificacion depende del peso, se debe consultar con el farmaceutico de "
                "turno o con el pediatra antes de administrar cualquier medicamento"
            ),
            "sugerencias": [],
            "aviso": AVISO_CLINICO,
        }

    bloqueados = _principios_bloqueados(alergias)
    sugerencias = []
    sin_coincidencia = []
    for sintoma in lista:
        coincidencia = None
        for clave, datos in SINTOMAS.items():
            if clave in sintoma or sintoma in clave:
                coincidencia = (clave, datos)
                break
        if coincidencia is None:
            sin_coincidencia.append(sintoma)
            continue
        clave, datos = coincidencia
        opciones = []
        for codigo in datos["medicamentos"]:
            medicamento = MEDICAMENTOS[codigo]
            # El producto se descarta cuando choca con una alergia declarada o con la edad del paciente
            if medicamento["principio_activo"] in bloqueados:
                continue
            if edad is not None and int(edad) < medicamento["edad_minima"]:
                continue
            opciones.append(
                {
                    "codigo": medicamento["codigo"],
                    "principio_activo": medicamento["principio_activo"],
                    "presentacion": medicamento["presentacion"],
                    "precio": medicamento["precio"],
                    "advertencias": medicamento["advertencias"],
                }
            )
        sugerencias.append({"sintoma": clave, "cuidados": datos["nota"], "opciones_venta_libre": opciones})

    urgencia = "autocuidado" if sugerencias else "consulta profesional"
    return {
        "urgencia": urgencia,
        "sintomas_evaluados": lista,
        "sintomas_sin_coincidencia": sin_coincidencia,
        "signos_de_alarma": [],
        "principios_descartados_por_alergia": sorted(bloqueados),
        "recomendacion": (
            "se sugieren productos de venta libre para alivio sintomatico, la seleccion final debe validarse con el "
            "farmaceutico de turno"
            if sugerencias
            else "los sintomas descritos no corresponden a un cuadro de autocuidado, se debe agendar consulta medica"
        ),
        "sugerencias": sugerencias,
        "aviso": AVISO_CLINICO,
    }


def verificar_interacciones(codigos_medicamentos):
    """Revisa si existen interacciones documentadas entre los medicamentos indicados."""
    codigos = [str(codigo).strip().upper() for codigo in (codigos_medicamentos or [])]
    if len(codigos) < 2:
        raise ErrorDominio("se deben indicar al menos dos medicamentos para verificar interacciones")

    principios = []
    for codigo in codigos:
        medicamento = MEDICAMENTOS.get(codigo)
        if medicamento is None:
            raise ErrorDominio(f"no existe el medicamento {codigo} en el catalogo")
        principios.append(medicamento["principio_activo"])

    hallazgos = []
    for interaccion in INTERACCIONES:
        if all(principio in principios for principio in interaccion["principios"]):
            hallazgos.append(interaccion)

    return {
        "medicamentos_evaluados": codigos,
        "principios_activos": principios,
        "total_interacciones": len(hallazgos),
        "interacciones": hallazgos,
        "recomendacion": (
            "existen interacciones documentadas, la combinacion debe validarse con el farmaceutico antes de despachar"
            if hallazgos
            else "no se encontraron interacciones documentadas entre los principios activos evaluados"
        ),
        "aviso": AVISO_CLINICO,
    }


def consultar_inventario(codigo_medicamento, codigo_sucursal=None):
    """Devuelve las existencias de un medicamento en una sucursal o en toda la cadena."""
    codigo = str(codigo_medicamento).strip().upper()
    medicamento = MEDICAMENTOS.get(codigo)
    if medicamento is None:
        raise ErrorDominio(f"no existe el medicamento {codigo} en el catalogo")

    if codigo_sucursal:
        sucursal = str(codigo_sucursal).strip().upper()
        if sucursal not in SUCURSALES:
            raise ErrorDominio(f"no existe la sucursal {sucursal}, los codigos validos tienen el formato SUC-01")
        claves = [sucursal]
    else:
        claves = list(SUCURSALES.keys())

    existencias = []
    for clave in claves:
        unidades = INVENTARIO.get(clave, {}).get(codigo, 0)
        existencias.append(
            {
                "codigo_sucursal": clave,
                "sucursal": SUCURSALES[clave]["nombre"],
                "municipio": SUCURSALES[clave]["municipio"],
                "unidades": unidades,
                "disponible": unidades > 0,
            }
        )
    return {
        "codigo": codigo,
        "principio_activo": medicamento["principio_activo"],
        "requiere_receta": medicamento["requiere_receta"],
        "precio": medicamento["precio"],
        "total_en_cadena": sum(elemento["unidades"] for elemento in existencias),
        "existencias": existencias,
    }


def crear_pedido(codigo_cliente, items, codigo_sucursal=None, tipo_entrega="retiro en sucursal"):
    """Registra un pedido validando receta, alergias, edad minima e inventario disponible."""
    codigo = str(codigo_cliente).strip().upper()
    cliente = CLIENTES.get(codigo)
    if cliente is None:
        raise ErrorDominio(f"no existe el cliente {codigo}, los codigos validos tienen el formato CLI-1001")

    if not items:
        raise ErrorDominio("el pedido debe contener al menos un medicamento")

    sucursal = str(codigo_sucursal).strip().upper() if codigo_sucursal else cliente["sucursal_preferida"]
    if sucursal not in SUCURSALES:
        raise ErrorDominio(f"no existe la sucursal {sucursal}, los codigos validos tienen el formato SUC-01")

    entrega = _normalizar(tipo_entrega)
    if entrega not in TIPOS_ENTREGA:
        raise ErrorDominio(f"la modalidad {tipo_entrega} no es valida, las admitidas son: {', '.join(TIPOS_ENTREGA)}")
    if entrega == "entrega a domicilio" and not SUCURSALES[sucursal]["servicio_domicilio"]:
        raise ErrorDominio(f"la sucursal {sucursal} no presta servicio a domicilio, se debe elegir retiro en sucursal")

    bloqueados = _principios_bloqueados(cliente["alergias"])
    detalle = []
    total = 0.0
    for item in items:
        codigo_medicamento = str(item.get("codigo_medicamento", "")).strip().upper()
        cantidad = int(item.get("cantidad", 1))
        medicamento = MEDICAMENTOS.get(codigo_medicamento)
        if medicamento is None:
            raise ErrorDominio(f"no existe el medicamento {codigo_medicamento} en el catalogo")
        if cantidad <= 0:
            raise ErrorDominio(f"la cantidad solicitada de {codigo_medicamento} debe ser mayor a cero")

        # Un medicamento de receta solo se despacha si el cliente tiene la receta registrada como vigente
        if medicamento["requiere_receta"] and codigo_medicamento not in cliente["receta_vigente"]:
            raise ErrorDominio(
                f"el medicamento {codigo_medicamento} de principio activo {medicamento['principio_activo']} requiere "
                f"receta medica vigente y el cliente {codigo} no tiene una registrada, el pedido no puede despacharse"
            )
        if medicamento["principio_activo"] in bloqueados:
            raise ErrorDominio(
                f"el medicamento {codigo_medicamento} contiene {medicamento['principio_activo']} y el cliente declaro "
                f"alergia a {', '.join(cliente['alergias'])}, el pedido no puede despacharse"
            )
        if cliente["edad"] < medicamento["edad_minima"]:
            raise ErrorDominio(
                f"el medicamento {codigo_medicamento} tiene una edad minima de {medicamento['edad_minima']} años y el "
                f"cliente tiene {cliente['edad']}, se requiere evaluacion profesional"
            )

        disponibles = INVENTARIO.get(sucursal, {}).get(codigo_medicamento, 0)
        if cantidad > disponibles:
            raise ErrorDominio(
                f"la sucursal {sucursal} tiene {disponibles} unidades de {codigo_medicamento} y se solicitaron "
                f"{cantidad}, se debe consultar el inventario de otra sucursal"
            )

        subtotal = round(medicamento["precio"] * cantidad, 2)
        total += subtotal
        detalle.append(
            {
                "codigo_medicamento": codigo_medicamento,
                "principio_activo": medicamento["principio_activo"],
                "presentacion": medicamento["presentacion"],
                "cantidad": cantidad,
                "precio_unitario": medicamento["precio"],
                "subtotal": subtotal,
                "requiere_receta": medicamento["requiere_receta"],
            }
        )

    # Las interacciones no bloquean el pedido pero se adjuntan como advertencia para el farmaceutico
    advertencias = []
    if len(detalle) > 1:
        revision = verificar_interacciones([elemento["codigo_medicamento"] for elemento in detalle])
        advertencias = revision["interacciones"]

    with CANDADO:
        datos = _cargar()
        datos["consecutivo"] = datos.get("consecutivo", 0) + 1
        identificador = f"PED-{datos['consecutivo']:05d}"
        horas = 2 if entrega == "retiro en sucursal" else 5
        pedido = {
            "codigo_pedido": identificador,
            "codigo_cliente": codigo,
            "cliente": cliente["nombre"],
            "codigo_sucursal": sucursal,
            "sucursal": SUCURSALES[sucursal]["nombre"],
            "tipo_entrega": entrega,
            "estado": "registrado",
            "detalle": detalle,
            "total": round(total, 2),
            "advertencias_interaccion": advertencias,
            "fecha_creacion": datetime.now().isoformat(timespec="seconds"),
            "fecha_estimada": (datetime.now() + timedelta(hours=horas)).isoformat(timespec="seconds"),
            "aviso": AVISO_CLINICO,
        }
        datos.setdefault("pedidos", {})[identificador] = pedido
        _guardar(datos)
    return pedido


def consultar_pedido(codigo_pedido):
    """Devuelve la informacion completa de un pedido."""
    identificador = str(codigo_pedido).strip().upper()
    datos = _cargar()
    pedido = datos.get("pedidos", {}).get(identificador)
    if pedido is None:
        raise ErrorDominio(f"no existe el pedido {identificador}")
    return pedido


def listar_pedidos(codigo_cliente=None, estado=None):
    """Devuelve los pedidos registrados filtrados por cliente o por estado."""
    datos = _cargar()
    resultado = []
    for pedido in datos.get("pedidos", {}).values():
        if codigo_cliente and pedido["codigo_cliente"] != str(codigo_cliente).strip().upper():
            continue
        if estado and pedido["estado"] != _normalizar(estado):
            continue
        resultado.append(pedido)
    resultado.sort(key=lambda elemento: elemento["fecha_creacion"], reverse=True)
    return {"total": len(resultado), "pedidos": resultado}


def actualizar_pedido(codigo_pedido, estado, nota=""):
    """Cambia el estado de un pedido y agrega una nota de seguimiento."""
    identificador = str(codigo_pedido).strip().upper()
    estado_normalizado = _normalizar(estado)
    if estado_normalizado not in ESTADOS_PEDIDO:
        raise ErrorDominio(f"el estado {estado} no es valido, los estados admitidos son: {', '.join(ESTADOS_PEDIDO)}")

    with CANDADO:
        datos = _cargar()
        pedido = datos.get("pedidos", {}).get(identificador)
        if pedido is None:
            raise ErrorDominio(f"no existe el pedido {identificador}")
        # Un pedido ya entregado se considera cerrado y no admite cambios de estado
        if pedido["estado"] == "entregado" and estado_normalizado != "entregado":
            raise ErrorDominio("un pedido entregado no puede cambiar de estado")
        pedido["estado"] = estado_normalizado
        pedido.setdefault("seguimiento", []).append(
            {"fecha": datetime.now().isoformat(timespec="seconds"), "estado": estado_normalizado, "nota": str(nota).strip()}
        )
        _guardar(datos)
    return pedido
