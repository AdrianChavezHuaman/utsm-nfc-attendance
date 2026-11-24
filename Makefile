# Shaula_efc — atajos de desarrollo
PY := .venv/bin/python
FLASK := .venv/bin/flask --app run.py

.PHONY: setup setup-dev bootstrap init seed seed-historico validar-historico demo-fase3 demo-fase4 run stop restart test smoke shots shots-bloque1 shots-bloque2 shots-bloque3 shots-bloque4 lint fmt fmt-check schema clean-db reset-db

setup: ## Crea el entorno virtual e instala dependencias
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip -q
	.venv/bin/pip install -r requirements.txt

setup-dev: ## Instala también herramientas de QA (ruff, selenium)
	.venv/bin/pip install -r requirements-dev.txt

bootstrap: ## Crea la base y carga los datos base
	$(FLASK) init-db
	$(FLASK) seed-base

init: ## Crea las tablas
	$(FLASK) init-db

seed: ## Carga datos maestros (idempotente)
	$(FLASK) seed-base

seed-historico: ## Genera la línea base 2024-2026 (marcas, incidencias y periodos)
	$(PY) seeds/seed_historico.py

validar-historico: ## Compara la base histórica con la Tabla 9 del documento
	$(PY) scripts/validar_historico.py

demo-fase3: ## Crea incidencias y una justificación de demostración
	$(PY) scripts/demo_fase3.py

demo-fase4: ## Genera marcas simuladas del mes anterior para el consolidado
	$(PY) scripts/demo_fase4.py

run: ## Levanta el servidor local
	@if ss -ltn 2>/dev/null | grep -q ':5000 '; then \
		echo "El puerto 5000 ya está en uso: probablemente ya hay un servidor corriendo."; \
		echo "  Abre http://127.0.0.1:5000 en el navegador,"; \
		echo "  o ejecuta 'make stop' si quieres reiniciarlo."; \
		exit 1; \
	fi
	$(PY) run.py

stop: ## Detiene el servidor local si el puerto 5000 está ocupado
	@if ! ss -ltn 2>/dev/null | grep -q ':5000 '; then \
		echo "El puerto 5000 ya está libre."; \
	else \
		pids=$$(ss -ltnp 2>/dev/null | grep ':5000 ' | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u | tr '\n' ' '); \
		echo "Deteniendo servidor (PID $$pids)…"; \
		kill $$pids 2>/dev/null || true; \
		sleep 1; \
		ss -ltn 2>/dev/null | grep -q ':5000 ' && echo "El puerto sigue ocupado; revisa con: ss -ltnp | grep :5000" || echo "Puerto 5000 libre."; \
	fi

restart: stop ## Reinicia el servidor local
	$(PY) run.py

test: ## Ejecuta la suite de pruebas
	.venv/bin/pytest -q

lint: ## Revisa estilo y posibles bugs con ruff
	.venv/bin/ruff check app seeds tests scripts run.py

fmt: ## Formatea el código Python con ruff
	.venv/bin/ruff format app seeds tests scripts run.py

fmt-check: ## Verifica el formato sin modificar archivos
	.venv/bin/ruff format --check app seeds tests scripts run.py

smoke: ## Prueba de humo con CSRF contra la base real (sin servidor)
	.venv/bin/python scripts/smoke_test.py

shots: ## Capturas visuales con Firefox (requiere make run en otra terminal)
	.venv/bin/python scripts/qa_screenshots.py

shots-bloque1: ## Evidencia visual AS-IS/TO-BE (requiere make run)
	.venv/bin/python scripts/qa_bloque1.py

shots-bloque2: ## Evidencia visual de asistencia y personal (requiere make run)
	.venv/bin/python scripts/qa_bloque2.py

shots-bloque3: ## Evidencia visual del consolidado anual (requiere make run)
	.venv/bin/python scripts/qa_bloque3.py

shots-bloque4: ## Evidencia visual de auditoría y acabado (requiere make run)
	.venv/bin/python scripts/qa_bloque4.py

shots-v7: ## Capturas definitivas para gestion_v7 (requiere make run)
	.venv/bin/python scripts/qa_v7.py

schema: ## Regenera schema.sql desde la base actual
	$(PY) scripts/export_schema.py

reset-db: ## Borra la base local (pide confirmación)
	$(FLASK) reset-db

clean-db: ## Borra la base local sin preguntar
	$(FLASK) reset-db --yes
