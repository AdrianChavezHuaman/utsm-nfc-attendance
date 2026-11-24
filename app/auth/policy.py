"""Política mínima de contraseñas del prototipo.

Se aplica al crear o restablecer una cuenta desde Administración.
Los usuarios de demostración del seed no pasan por esta validación.
"""

LARGO_MINIMO = 8

REGLAS = (
    f"Al menos {LARGO_MINIMO} caracteres.",
    "Al menos una letra y un número.",
    "Sin espacios en blanco.",
)


def errores_password(password: str) -> list[str]:
    """Devuelve los incumplimientos de la política para una contraseña."""
    errores: list[str] = []
    if len(password) < LARGO_MINIMO:
        errores.append(f"Usa al menos {LARGO_MINIMO} caracteres.")
    if not any(caracter.isalpha() for caracter in password):
        errores.append("Incluye al menos una letra.")
    if not any(caracter.isdigit() for caracter in password):
        errores.append("Incluye al menos un número.")
    if any(caracter.isspace() for caracter in password):
        errores.append("La contraseña no debe tener espacios.")
    return errores


def texto_politica() -> str:
    """Resume la política para mostrarla en el formulario."""
    return " ".join(REGLAS)
