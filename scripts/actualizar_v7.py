"""Genera gestion_v7.docx a partir de gestion_v6.docx.

Uso:
    .venv/bin/python scripts/actualizar_v7.py

El script trabaja sobre una copia: nunca abre en modo escritura el v6.
Actualiza el texto del prototipo, las fichas S1/S2, agrega la sección de
verificación y el anexo con las 31 capturas.
"""

import copy
import re
import shutil
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ORIGEN = PROJECT_ROOT.parent / "gestion_v6.docx"
DESTINO = PROJECT_ROOT.parent / "gestion_v7.docx"
CAPTURAS = PROJECT_ROOT / "docs" / "capturas" / "v7"
MANIFIESTO = CAPTURAS / "MANIFIESTO.md"

sys.path.insert(0, str(PROJECT_ROOT))
from app import create_app  # noqa: E402
from app.models import Incidencia, Marca, Periodo, Tarjeta, Trabajador  # noqa: E402


# ---------------------------------------------------------------------------
# Utilidades de edición
# ---------------------------------------------------------------------------
def poner_texto(parrafo: Paragraph, texto: str) -> None:
    """Reemplaza el texto sin perder la fuente del primer run."""
    if not parrafo.runs:
        run = parrafo.add_run(texto)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        return
    parrafo.runs[0].text = texto
    for run in parrafo.runs[1:]:
        run.text = ""


def poner_celda(celda: _Cell, texto: str) -> None:
    poner_texto(celda.paragraphs[0], texto)
    for extra in celda.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)


def clonar_antes(ancla: Paragraph, modelo: Paragraph) -> Paragraph:
    nueva = copy.deepcopy(modelo._p)
    ancla._p.addprevious(nueva)
    return Paragraph(nueva, ancla._parent)


def clonar_despues(ancla: Paragraph, modelo: Paragraph) -> Paragraph:
    nueva = copy.deepcopy(modelo._p)
    ancla._p.addnext(nueva)
    return Paragraph(nueva, ancla._parent)


def buscar(doc: Document, inicio: str) -> Paragraph:
    encontrados = [p for p in doc.paragraphs if p.text.strip().startswith(inicio)]
    if len(encontrados) != 1:
        raise RuntimeError(
            f"Se esperaba un párrafo que empiece con {inicio!r}; hay {len(encontrados)}"
        )
    return encontrados[0]


def datos_de_la_base() -> dict:
    aplicacion = create_app()
    with aplicacion.app_context():
        return {
            "trabajadores": Trabajador.query.count(),
            "tarjetas": Tarjeta.query.count(),
            "marcas": Marca.query.count(),
            "incidencias": Incidencia.query.count(),
            "periodos": Periodo.query.count(),
        }


def capturas_del_manifiesto() -> list[tuple[str, str]]:
    texto = MANIFIESTO.read_text(encoding="utf-8")
    filas = []
    for linea in texto.splitlines():
        coincide = re.match(r"\|\s*A\d+\s*\|\s*`([^`]+\.png)`\s*\|\s*(.+?)\s*\|", linea)
        if not coincide:
            continue
        archivo = coincide.group(1)
        detalle = coincide.group(2)
        titulo = detalle.split(". ")[0].strip()
        filas.append((archivo, titulo))
    if len(filas) != 31:
        raise RuntimeError(f"El manifiesto debería tener 31 figuras; tiene {len(filas)}")
    return filas


# ---------------------------------------------------------------------------
# Edición del documento
# ---------------------------------------------------------------------------
def actualizar_prototipo(doc: Document, datos: dict) -> None:
    encabezado = buscar(doc, "4.4. DISEÑO PRELIMINAR")
    poner_texto(encabezado, "4.4. PROTOTIPO FUNCIONAL DE LA INTERFAZ")

    intro = buscar(doc, "El prototipo de interfaz no se ha implementado")
    poner_texto(
        intro,
        "El prototipo se construyó como una aplicación local en Flask con base de datos "
        "SQLite. Se ejecuta en un equipo con el comando python run.py y no depende de "
        "hosting ni de servicios externos. La interfaz sigue el flujo descrito en el "
        "diseño: marcación, incidencias, justificaciones, consolidación y reportes.",
    )

    poner_texto(buscar(doc, "4.4.1. PANTALLAS PREVISTAS"), "4.4.1. PANTALLAS IMPLEMENTADAS")

    resumen = buscar(doc, "La propuesta contempla cinco pantallas")
    poner_texto(
        resumen,
        "El prototipo implementa las cinco pantallas previstas y agrega tres módulos que "
        "el diseño inicial no detallaba: asistencia diaria con ficha individual, "
        "consolidado anual con comparaciones y auditoría legible. La navegación cambia "
        "según el rol de la cuenta.",
    )

    reemplazos = {
        "• Acceso:": (
            "• Acceso: inicio de sesión con correo institucional y contraseña, bloqueo tras "
            "cinco intentos fallidos, cierre por inactividad y registro de cada acceso."
        ),
        "• Kiosco de marcación:": (
            "• Kiosco de marcación: pantalla pública en la sede; confirma la tarjeta, la "
            "hora, la sede y el tipo de marcación, y bloquea los duplicados."
        ),
        "• Panel de control:": (
            "• Panel de control: resume marcaciones, incidencias, justificaciones "
            "pendientes, periodos y adopción NFC; los KPI 2024-2026 son línea base y 2027 "
            "es meta."
        ),
        "• Gestión de incidencias:": (
            "• Gestión de incidencias: lista del trabajador, justificación con archivo, "
            "bandeja del coordinador y detalle con aprobación o rechazo."
        ),
        "• Reportes:": (
            "• Reportes: preconsolidado mensual, cierre con archivos y consolidado anual "
            "con filtros, comparaciones y vista semestral."
        ),
    }
    for inicio, texto in reemplazos.items():
        poner_texto(buscar(doc, inicio), texto)

    # Dos viñetas nuevas después de la última
    ultima = buscar(doc, "• Reportes:")
    nuevas = [
        "• Asistencia y personal: tablero diario, ficha mensual con calendario y lista, "
        "y horario semanal por trabajador.",
        "• Auditoría: registro de acciones con lectura humana y cambios antes y después.",
    ]
    ancla = ultima
    for texto in nuevas:
        creada = clonar_despues(ancla, ultima)
        poner_texto(creada, texto)
        ancla = creada

    alcance = buscar(doc, "El prototipo será una aplicación local")
    poner_texto(
        alcance,
        "El prototipo es una aplicación local para PC, con fines académicos. No incluye "
        "hosting, PostgreSQL, integración con planilla ni lector NFC físico: el kiosco se "
        "opera con tarjetas de demostración. La base contiene "
        f"{datos['trabajadores']} trabajadores, {datos['tarjetas']} tarjetas, "
        f"{datos['marcas']:,} marcaciones, {datos['incidencias']:,} incidencias y "
        f"{datos['periodos']} periodos mensuales. Treinta y seis periodos corresponden a "
        "2024-2026 y uno a enero de 2027, que es una simulación.",
    )

    limite = buscar(doc, "Esta delimitación evita presentar como terminado")
    poner_texto(
        limite,
        "El alcance separa dos cosas: el prototipo demuestra que el flujo se puede "
        "ejecutar y medir; no demuestra que la institución haya reducido horas o costo. "
        "Esa comprobación corresponde al piloto.",
    )

    roles = buscar(doc, "La interfaz aplicará el principio de mínimo privilegio")
    poner_texto(
        roles,
        "La interfaz aplica el principio de mínimo privilegio. El trabajador ve solo sus "
        "marcaciones y sus justificaciones; el coordinador, su área; el analista, todas "
        "las sedes; y el jefe autoriza el cierre. Cada consulta y cada cambio quedan en "
        "el registro de auditoría con usuario, fecha, hora y acción.",
    )

    imagenes = buscar(doc, "Las imágenes de las pantallas se agregarán")
    poner_texto(
        imagenes,
        "Las capturas del prototipo se incluyen en el Anexo A, Figuras A1 a A31. "
        "Corresponden a una base con datos ficticios y no a una implantación real.",
    )

    # 4.4.4 Seguridad del acceso, antes de 4.5
    ancla = buscar(doc, "4.5. MATRIZ DE PROCESOS TO-BE")
    modelo_titulo = buscar(doc, "4.3.6. REGLAS DE VALIDACIÓN")
    modelo_cuerpo = buscar(doc, "Las reglas convierten las políticas")
    titulo = clonar_antes(ancla, modelo_titulo)
    poner_texto(titulo, "4.4.4. SEGURIDAD DEL ACCESO")
    parrafo = clonar_antes(ancla, modelo_cuerpo)
    poner_texto(
        parrafo,
        "El acceso se protege con contraseña almacenada como hash, cinco intentos "
        "fallidos y bloqueo de quince minutos. La sesión se cierra a los treinta minutos "
        "sin actividad. Las páginas privadas no se guardan en la caché del navegador y "
        "las respuestas incluyen cabeceras para evitar la interpretación del tipo de "
        "contenido y la inclusión en marcos.",
    )
    parrafo = clonar_antes(ancla, modelo_cuerpo)
    poner_texto(
        parrafo,
        "El sistema no guarda la huella en la base central: la usa solo como respaldo en "
        "el lector. La tarjeta se asocia a un código institucional y el registro conserva "
        "fecha, hora, sede y tipo de marcación. Cada acceso, cada bloqueo y cada "
        "corrección quedan en la auditoría.",
    )


def actualizar_evaluacion(doc: Document) -> None:
    intro = buscar(doc, "Este capítulo no presenta resultados reales")
    poner_texto(
        intro,
        "Este capítulo no presenta resultados de una implantación real. La universidad es "
        "ficticia y el prototipo es local; por lo tanto, las cifras de 2027 son metas de "
        "diseño y enero de 2027 es una simulación. La validación requiere un piloto con "
        "datos reales.",
    )

    fichas = buscar(doc, "Las fichas se construyen después del TO-BE")
    poner_texto(
        fichas,
        fichas.text.rstrip()
        + " La meta anual se descompone en dos semestres: el primero refleja la adopción "
        "gradual y el segundo la operación plena.",
    )

    nota_tabla9 = buscar(doc, "Nota. Los valores 2024-2026 son la línea base")
    poner_texto(
        nota_tabla9,
        nota_tabla9.text.rstrip()
        + " Las fichas 33 a 35 descomponen la meta 2027 en semestres; el valor anual es "
        "el agregado de ambos, no su promedio.",
    )


def actualizar_fichas(doc: Document) -> None:
    valores = {
        32: ("90 %", "100 %"),
        35: ("40 h", "28 h"),
        38: ("8 %", "4 %"),
    }
    for indice, (s1, s2) in valores.items():
        tabla = doc.tables[indice]
        celdas = tabla.rows[10]._tr.tc_lst
        poner_celda(_Cell(celdas[1], tabla), s1)
        poner_celda(_Cell(celdas[2], tabla), s2)


def agregar_verificacion(doc: Document) -> None:
    ancla = buscar(doc, "CAPÍTULO VI")
    modelo_titulo = buscar(doc, "5.4. COSTO, AHORRO Y SENSIBILIDAD")
    modelo_cuerpo = buscar(doc, "La inversión inicial estimada es S/ 16,000")
    modelo_caption = buscar(doc, "Tabla 27")
    modelo_nota = buscar(doc, "Nota. Las cifras del TO-BE son metas, no mediciones")
    tabla_modelo = doc.tables[10]

    def insertar_titulo(texto: str) -> None:
        parrafo = clonar_antes(ancla, modelo_titulo)
        poner_texto(parrafo, texto)

    def insertar_cuerpo(texto: str) -> None:
        parrafo = clonar_antes(ancla, modelo_cuerpo)
        poner_texto(parrafo, texto)

    parrafo = clonar_antes(ancla, modelo_cuerpo)
    poner_texto(
        parrafo,
        "Las fichas 33 a 35 descomponen la meta 2027 en semestres. En oportunidad, el "
        "primer semestre cierra 9 de 10 periodos y el segundo los 10; el anual es "
        "19/20 = 95 %. En eficiencia, el primer semestre consume 40 h/mes y el segundo "
        "28 h/mes; el promedio anual es 34 h/mes. En calidad, el primer semestre registra "
        "8 % y el segundo 4 %; el anual es 6 %. El valor anual es el agregado de los "
        "semestres, no un promedio simple de porcentajes.",
    )

    insertar_titulo("5.7. CÓMO SE VERIFICA LA MEJORA")
    insertar_cuerpo(
        "La comparación entre el AS-IS y el TO-BE se sostiene en tres niveles. El primero "
        "es el mecanismo: cada problema de la Tabla 18 tiene una acción del TO-BE que lo "
        "elimina o lo reduce. El segundo es la proyección: la Tabla 27 estima el efecto "
        "con las mismas fórmulas del AS-IS. El tercero es la medición: el piloto de ocho "
        "semanas de la sección 5.3 reemplaza la estimación por datos observados."
    )
    insertar_cuerpo(
        "El prototipo cumple una función distinta de la del piloto. Permite ejecutar el "
        "flujo completo y comprobar que los indicadores se calculan; no demuestra que la "
        "institución haya ahorrado horas. Por eso, sus capturas se presentan como "
        "evidencia de funcionamiento, no como resultado de la mejora."
    )
    insertar_cuerpo(
        "Para que la comparación sea válida se mantienen cuatro condiciones: la misma "
        "fórmula en ambos escenarios, el mismo periodo, la misma sede y la misma "
        "población. La adopción NFC se mide como condición: si no llega a 95 %, el TO-BE "
        "no se está ejecutando y la comparación se detiene. El piloto debe incluir una "
        "semana de capacitación y siete de operación."
    )
    insertar_cuerpo(
        "Antes del piloto se define qué resultado refutaría la propuesta. Si el tiempo de "
        "consolidación no baja de 10 h/mes, si las justificaciones extraviadas siguen por "
        "encima de 10 % o si la adopción no alcanza 90 %, el TO-BE no mejora en esa "
        "dimensión y se ajusta el proceso o la regla. El indicador no se cambia para que "
        "cuadre."
    )

    caption = clonar_antes(ancla, modelo_caption)
    poner_texto(caption, "Tabla 36")
    run = caption.add_run("\n")
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run = caption.add_run("Niveles de evidencia para comparar el AS-IS y el TO-BE")
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.italic = True
    nueva = copy.deepcopy(tabla_modelo._tbl)
    caption._p.addnext(nueva)
    tabla = Table(nueva, caption._parent)
    fila_extra = copy.deepcopy(tabla.rows[-1]._tr)
    tabla._tbl.append(fila_extra)

    filas = [
        ("Nivel de evidencia", "Qué aporta", "Qué no permite afirmar"),
        ("Parámetros 2024-2026", "Magnitud del problema", "Que sean mediciones reales"),
        ("Meta 2027", "Efecto esperado", "Que la mejora ya ocurrió"),
        ("Enero 2027 simulado", "Que el sistema mide y compara", "Que el TO-BE funcione"),
        ("Piloto", "Si la mejora ocurrió", "Nada hasta que se ejecute"),
    ]
    for numero, valores in enumerate(filas):
        for columna, texto in enumerate(valores):
            poner_celda(tabla.rows[numero].cells[columna], texto)

    # La tabla quedó entre la caption y el ancla; la nota va después de la tabla
    nota = clonar_antes(ancla, modelo_nota)
    poner_texto(nota, "Nota. ")
    run = nota.add_run(
        "El nivel de evidencia indica qué se puede afirmar con cada dato. "
        "La comparación final corresponde al piloto."
    )
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)


def actualizar_conclusiones(doc: Document) -> None:
    intro = buscar(doc, "Las conclusiones se refieren al diseño y a la estimación ex ante")
    poner_texto(
        intro,
        "Las conclusiones se refieren al diseño, al prototipo y a la estimación ex ante; "
        "no sustituyen una evaluación con datos reales. El piloto queda pendiente.",
    )

    solucion = buscar(doc, "La solución tecnológica se especificó")
    poner_texto(
        solucion,
        "La solución tecnológica se especificó con una arquitectura por capas, nueve "
        "entidades, catorce requerimientos funcionales, diez no funcionales, siete casos "
        "de uso, diez reglas de validación y cinco pantallas. Esa especificación se llevó "
        "a un prototipo local que ejecuta el flujo completo y permite medir los "
        "indicadores; no es una implantación institucional.",
    )

    creada = clonar_despues(solucion, solucion)
    poner_texto(
        creada,
        "El prototipo se construyó con Flask y SQLite. Cubre acceso por roles, kiosco, "
        "incidencias, justificaciones, asistencia, consolidado mensual y anual, corrección "
        "de marcas y auditoría. Se probó con 135 pruebas automáticas y una lista de "
        "comprobaciones de extremo a extremo; esas pruebas verifican el funcionamiento "
        "del software, no el desempeño del proceso.",
    )


def agregar_anexo(doc: Document) -> None:
    figuras = capturas_del_manifiesto()

    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    titulo.paragraph_format.page_break_before = True
    run = titulo.add_run("ANEXOS")
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.bold = True

    subtitulo = doc.add_paragraph()
    run = subtitulo.add_run("Anexo A. Evidencia del prototipo")
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.bold = True

    intro = doc.add_paragraph()
    poner_texto(
        intro,
        "Las figuras A1 a A31 corresponden al prototipo local con datos ficticios. Los "
        "indicadores de 2024 a 2026 son la línea base; 2027 es una meta y enero de 2027 "
        "es una simulación. Cada figura indica la pantalla y el elemento que se quiere "
        "mostrar.",
    )

    for indice, (archivo, titulo_figura) in enumerate(figuras, start=1):
        caption = doc.add_paragraph()
        caption.alignment = WD_ALIGN_PARAGRAPH.LEFT
        caption.paragraph_format.space_before = Pt(12)
        caption.paragraph_format.keep_with_next = True
        run = caption.add_run(f"Figura A{indice}\n")
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.font.bold = True
        run = caption.add_run(titulo_figura)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.font.italic = True

        imagen = doc.add_paragraph()
        imagen.alignment = WD_ALIGN_PARAGRAPH.CENTER
        imagen.paragraph_format.keep_with_next = True
        ancho = Cm(6) if "movil" in archivo else Cm(12)
        imagen.add_run().add_picture(str(CAPTURAS / archivo), width=ancho)

        nota = doc.add_paragraph()
        run = nota.add_run("Nota. ")
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.font.italic = True
        run = nota.add_run("Fuente: elaboración propia con datos ficticios del prototipo (2026).")
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)


def verificar(doc: Document) -> None:
    texto = "\n".join(p.text for p in doc.paragraphs)
    prohibidas = [
        "no se ha implementado",
        "aún no implementadas",
        "se construirán en la segunda etapa",
        "software que aún no existe",
        "se agregarán cuando el prototipo esté construido",
    ]
    for frase in prohibidas:
        if frase in texto:
            raise RuntimeError(f"Quedó una frase del estado anterior: {frase!r}")
    if "Figura A31" not in texto:
        raise RuntimeError("No se agregó el anexo completo")
    if len(doc.tables) != 42:
        raise RuntimeError(f"Se esperaban 42 tablas; hay {len(doc.tables)}")
    from docx.oxml.ns import qn

    dibujos = len(list(doc.element.body.iter(qn("w:drawing"))))
    if dibujos != 38:
        raise RuntimeError(f"Se esperaban 38 imágenes; hay {dibujos}")


def main() -> int:
    if not ORIGEN.exists():
        print(f"No existe el documento de origen: {ORIGEN}")
        return 1
    if DESTINO.exists():
        DESTINO.unlink()
    shutil.copy2(ORIGEN, DESTINO)

    doc = Document(DESTINO)
    datos = datos_de_la_base()
    actualizar_prototipo(doc, datos)
    actualizar_evaluacion(doc)
    actualizar_fichas(doc)
    agregar_verificacion(doc)
    actualizar_conclusiones(doc)
    agregar_anexo(doc)
    verificar(doc)
    doc.save(DESTINO)

    print(f"Documento generado: {DESTINO}")
    print(f"Párrafos: {len(doc.paragraphs)}; tablas: {len(doc.tables)}")
    print(
        "Datos usados: "
        f"{datos['trabajadores']} trabajadores, {datos['marcas']:,} marcas, "
        f"{datos['incidencias']:,} incidencias, {datos['periodos']} periodos"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
