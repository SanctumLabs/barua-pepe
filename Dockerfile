FROM python:3.10.0-alpine3.11

WORKDIR /usr/src/app

COPY . .

RUN pip install pipenv
RUN pipenv lock -r > requirements.txt
RUN pip install -r requirements.txt

EXPOSE 6000

CMD ["gunicorn", "--config", "config/gunicorn_config.py", "wsgi:app"]
