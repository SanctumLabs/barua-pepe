# Installs dependencies
install:
	pipenv install

# Runs application
run:
	python asgi_server.py

# Runs the application with reload flag set
run-reload:
	uvicorn app:app --port 5000 --reload

# Runs the worker
run-worker:
	celery -A app.worker.celery_app worker --events -l info -n barua-pepe-worker@%n --concurrency=5

# Runs tests
test:
	pytest

# Runs tests with coverage
test-cover:
	pytest --cov=app tests/

# Runs a local SMTP debugging server which will print out the message in the terminal window & discard them. This allows
# for local testing
smtp-server:
	python -m smtpd -c DebuggingServer -n localhost:1025

format:
	black app

lint:
	pylint app

load-test:
	locust --config .locust.conf
