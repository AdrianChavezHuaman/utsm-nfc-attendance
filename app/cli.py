"""Comandos de línea de comandos (Flask CLI)."""

import click

from .extensions import db


def register_cli(app) -> None:
    @app.cli.command("init-db")
    def init_db():
        """Crea todas las tablas en la base local."""
        db.create_all()
        click.echo("Base de datos inicializada en instance/asistencia.db")

    @app.cli.command("seed-base")
    def seed_base_command():
        """Carga sedes, áreas, trabajadores, tarjetas, horarios y usuarios."""
        from seeds.seed_base import seed_base

        resumen = seed_base()
        if resumen.get("existente"):
            click.echo("Los datos base ya estaban cargados; no se duplicó nada.")
            return
        for clave, valor in resumen.items():
            click.echo(f"  {clave}: {valor}")
        click.echo("Datos base cargados correctamente.")

    @app.cli.command("bootstrap")
    def bootstrap():
        """Crea la base y carga los datos base en un solo paso."""
        db.create_all()
        from seeds.seed_base import seed_base

        resumen = seed_base()
        if resumen.get("existente"):
            click.echo("Base ya existente. Datos base sin cambios.")
        else:
            click.echo("Base creada y datos base cargados.")
            for clave, valor in resumen.items():
                click.echo(f"  {clave}: {valor}")

    @app.cli.command("seed-historico")
    @click.option(
        "--anio",
        "anios",
        multiple=True,
        type=int,
        help="Año a generar (2024, 2025 o 2026). Se puede repetir.",
    )
    @click.option("--objetivo", type=int, default=19520, help="Marcas objetivo por mes.")
    @click.option("--reemplazar", is_flag=True, help="Borra y regenera meses con marcas.")
    @click.option("--conservar-vacios", is_flag=True, help="No elimina periodos vacíos.")
    def seed_historico_command(anios, objetivo, reemplazar, conservar_vacios):
        """Genera la línea base histórica 2024-2026."""
        from seeds.seed_historico import ANIOS_VALIDOS, generar_historico

        seleccionados = list(anios) or list(ANIOS_VALIDOS)
        try:
            resumen = generar_historico(
                anios=seleccionados,
                objetivo_mensual=objetivo,
                reemplazar=reemplazar,
                conservar_vacios=conservar_vacios,
            )
        except ValueError as error:
            raise click.ClickException(str(error)) from error

        totales = resumen["totales"]
        click.echo(
            f"Histórico generado: {len(resumen['generados'])} periodos, "
            f"{totales['marcas']:,} marcas y {totales['incidencias']:,} incidencias."
        )
        if resumen["omitidos"]:
            click.echo(f"Omitidos con datos: {', '.join(resumen['omitidos'])}")

    @app.cli.command("reset-db")
    @click.option("--yes", is_flag=True, help="Confirma el borrado sin preguntar.")
    def reset_db(yes: bool):
        """Elimina todas las tablas de la base local."""
        if not yes:
            click.confirm("Se borrarán todos los datos locales. ¿Continuar?", abort=True)
        db.drop_all()
        db.create_all()
        click.echo("Base de datos reiniciada (vacía).")
