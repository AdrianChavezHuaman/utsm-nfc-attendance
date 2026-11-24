"""Formularios de justificación y decisión."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

EXTENSIONES_PERMITIDAS = ["pdf", "png", "jpg", "jpeg"]


class JustificacionForm(FlaskForm):
    motivo = TextAreaField(
        "Motivo de la justificación",
        validators=[
            DataRequired(message="Describe el motivo de la incidencia."),
            Length(min=10, max=2000, message="El motivo debe tener entre 10 y 2000 caracteres."),
        ],
    )
    archivo = FileField(
        "Sustento digital",
        validators=[
            FileAllowed(
                EXTENSIONES_PERMITIDAS,
                "Adjunta un archivo PDF, PNG, JPG o JPEG.",
            )
        ],
    )
    submit = SubmitField("Enviar justificación")


class DecisionForm(FlaskForm):
    comentario = TextAreaField(
        "Comentario de la decisión",
        validators=[Optional(), Length(max=500, message="Máximo 500 caracteres.")],
    )
    aprobar = SubmitField("Aprobar")
    rechazar = SubmitField("Rechazar")
