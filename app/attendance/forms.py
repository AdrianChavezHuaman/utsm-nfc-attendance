"""Formulario de corrección manual de marcaciones."""

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField, TextAreaField, TimeField
from wtforms.fields.choices import SelectChoice
from wtforms.validators import DataRequired, Length
from wtforms.widgets import Input


class TextoSimple(Input):
    """Campo de texto sin validaciones HTML nativas."""

    validation_attrs: tuple[str, ...] = ()


TIPOS_MARCA_FORM = (
    SelectChoice("ingreso", "Ingreso"),
    SelectChoice("salida", "Salida"),
)


class CorreccionMarcaForm(FlaskForm):
    fecha = DateField(
        "Fecha",
        format="%d/%m/%Y",
        widget=TextoSimple(input_type="text"),
        validators=[DataRequired(message="Indica la fecha de la marcación.")],
    )
    hora = TimeField(
        "Hora",
        format="%H:%M",
        widget=TextoSimple(input_type="text"),
        validators=[DataRequired(message="Indica la hora de la marcación.")],
    )
    tipo = SelectField(
        "Tipo de marcación",
        choices=TIPOS_MARCA_FORM,
        validators=[DataRequired(message="Selecciona el tipo de marcación.")],
    )
    motivo = TextAreaField(
        "Motivo de la corrección",
        validators=[
            DataRequired(message="Explica por qué se corrige la marcación."),
            Length(
                min=8,
                max=280,
                message="El motivo debe tener entre 8 y 280 caracteres.",
            ),
        ],
    )
    submit = SubmitField("Guardar corrección")
