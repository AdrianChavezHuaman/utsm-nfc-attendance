"""Formularios de autenticación."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class LoginForm(FlaskForm):
    correo = StringField(
        "Correo institucional",
        validators=[
            DataRequired(message="Ingresa tu correo institucional."),
            Email(message="El formato del correo no es válido."),
            Length(max=150),
        ],
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired(message="Ingresa tu contraseña.")],
    )
    recordarme = BooleanField("Mantener sesión iniciada")
    submit = SubmitField("Ingresar al sistema")
