FROM python:3.10.5-slim

WORKDIR /usr/src/app

# Declare container user variables
ARG CONTAINER_USER_NAME=barua-pepe
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN set -x \
# create baruapepe user/group first, to be consistent throughout docker variants
    && addgroup --system ${CONTAINER_USER_NAME} || true \
    && adduser --system --ingroup ${CONTAINER_USER_NAME} --home /home/${CONTAINER_USER_NAME} --gecos "${CONTAINER_USER_NAME} user" --shell /bin/false  ${CONTAINER_USER_NAME}

COPY . .

RUN pip install pipenv
RUN pipenv lock -r > requirements.txt
RUN pip install -r requirements.txt --no-cache-dir

USER $CONTAINER_USER_NAME

EXPOSE 5000

CMD ["python", "asgi_server.py"]
