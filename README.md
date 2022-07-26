# Barua Pepe

[![semantic-release](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg)](https://github.com/semantic-release/semantic-release)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Code Scanning](https://github.com/SanctumLabs/barua-pepe/actions/workflows/codeql.yml/badge.svg)](https://github.com/SanctumLabs/barua-pepe/actions/workflows/codeql.yml)
[![Lint](https://github.com/SanctumLabs/barua-pepe/actions/workflows/lint.yml/badge.svg)](https://github.com/SanctumLabs/barua-pepe/actions/workflows/lint.yml)
[![Tests](https://github.com/SanctumLabs/barua-pepe/actions/workflows/tests.yml/badge.svg)](https://github.com/SanctumLabs/barua-pepe/actions/workflows/tests.yml)
[![Docker](https://github.com/SanctumLabs/barua-pepe/actions/workflows/docker.yml/badge.svg)](https://github.com/SanctumLabs/barua-pepe/actions/workflows/docker.yml)

_Barua Pepe_ means email in Swahili & the intention of this project is to create a Simple Email Gateway that is
extensible, scalable & reliable to handle sending of emails in a platform. This can be included as part of a
notification system platform to handle integration with 3rd Party email providers or deployed as its own offering.

Underneath there are already integrations with email providers, but these can be changed to accommodate others if need
be.
By default, SMTP is used to send out emails, but will default to a 3rd party email provider if this fails.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing
purposes. See deployment for notes on how to deploy the project on a live system.

### Pre-requisites

Any editor of your choice can be used for this application.

1. [Python](https://www.python.org)

   This project has been built with Python 3.10. Ensure that you install this version of Python as outlined in the
   link provided [here](https://www.python.org/downloads/)

2. [Pip](https://pip.pypa.io/en/stable/)

   This is a package manager for Python applications and will be useful when handling dependencies
   for this application. Installations instructions can be found in the link int the title.

3. [Pipenv](https://pipenv.readthedocs.io/en/latest/)

   An awesome dependency management tool for Python and is highly recommended. This is the preferred
   tool of choice for this project. This allows use to separate between dev dependencies and dependencies

4. [Docker](https://www.docker.com/)

   This will be used when containerizing the application for running in a SOA(Service Oriented Architecture). This is
   used especially when deployment. Allows this application to run in any environment with minimal configuration.

First of, create a `.env` file which will contain environment variables for configurations of the application. This file
is not checked into VCS(Version Control System). An example file is found in [.env.example](./.env.example). Each
environment
variable use is described in it.

## Installing

You will first need to install the dependencies as specified in the Pipfile file by running:

` pipenv install `

## Running the application

1. Start by first running `docker-compose up` in root of project to run services required/needed by this service.
2. Run Dev server of application with either of the following commands:
    1. `python asgi_server.py`
    2. `uvicorn app:app --port 5000 --reload`
    3. `make run`
    4. `make run-reload`
3. Run celery workers with either:
    1. `celery -A app.worker.celery_app worker --events -l info -n barua-pepe-worker@%n --concurrency=5`
    2. `make run-worker`

With the application running feel free to test out the API. The docs will be available on http://localhost:5000/docs

## Application setup

Now that you have a default running setup of the application, you can tailor it to your needs.

There is the tree view of the current application:

```plain
app
|-- __init__.py
|-- api
|   |-- __init__.py
|   |-- dto.py
|   |-- mailer
|   |   |-- __init__.py
|   |   |-- dto.py
|   |   `-- routes.py
|   `-- monitoring
|       |-- __init__.py
|       `-- routes.py
|-- config.py
|-- constants.py
|-- domain
|   |-- __init__.py
|   |-- entities
|   |   |-- __init__.py
|   |   |-- email_attachment.py
|   |   |-- email_recipient.py
|   |   |-- email_request.py
|   |   `-- email_sender.py
|   `-- send_email.py
|-- exceptions.py
|-- infra
|   |-- __init__.py
|   |-- handlers
|   |   |-- __init__.py
|   |   `-- exception_handlers.py
|   `-- middleware
|       |-- __init__.py
|       `-- middleware.py
|-- logger.py
|-- services
|   |-- __init__.py
|   |-- auth
|   |   |-- __init__.py
|   |   `-- auth_service.py
|   `-- mail
|       |-- __init__.py
|       |-- email_service.py
|       |-- exceptions.py
|       |-- mailchimp_email_service.py
|       |-- mailer.py
|       |-- sendgrid_email_service.py
|       |-- smtp_proxy.py
|       `-- types.py
|-- tasks
|   |-- __init__.py
|   |-- exceptions.py
|   |-- mail_error_task.py
|   `-- mail_sending_task.py
|-- utils
|   `-- __init__.py
`-- worker
    |-- __init__.py
    `-- celery_app.py
```

This setup has been configured to be hexagonal to allow separation of concerns. For example, we could switch out which
type
of logger implementation directly in the [logger](./app/logger.py) without affecting the rest of the application.
Additionally,
we could also switch out how we do authentication in the [auth_service](./app/services/auth/auth_service.py) with
something else
maybe even a 3rd party authentication system.

The application uses Workers to handle the actual mail sending, this is to offload the application and allow it to serve
more requests.
The worker application and it's configuration can be found in [worker](./app/worker). This
uses [Celery](https://docs.celeryq.dev/en/stable/) & can be configured further based on the needs of a system. The
actual tasks
can be found in [tasks](./app/tasks) & more tasks can be added to tailer certain use cases. These tasks will be
discovered by the celery application, new tasks should be added here.

Celery Result backend options can be found
documented [here](https://docs.celeryq.dev/en/stable/userguide/configuration.html#conf-redis-result-backend) & if
another result backend is needed, you can follow the instructions there to setup and configure within the application.

REST API endpoints & routes can be found in the [api](./app/api) package. The actual application
uses [FastAPI](https://fastapi.tiangolo.com/) framework. This can be found [here](./app/__init__.py) along
with [config](./app/config.py) which is used to setup the application. These configurations are derived from environment
variables as defined [here](./.env.example). If these need to be changed, this is where that's done.

The [domain](./app/domain) contains the use cases of the application or the intent which drives what the application can
and can not do. This means if you intend to extend it to do more than email sending, you can define this here & then
drive that intent outwards to meet the need(Following a Hexagonal architecture approach).

[Infra](./app/infra) contains _infrastructure_ setup like [middleware](./app/infra/middleware)
and [handlers](./app/infra/handlers) that do not affect the overal running of the application but do add more
functionality to it. Middleware like logging, authentication, metrics can be added here based on the requirements.

[Services](./app/services) contain external services that interact with other systems using whatever protocol these 3rd
party systems can understand(REST, gRPC, SOAP, Message Queues etc.). This is where the actual mail sending happens for
this application.
You will notice that it contains [auth](./app/services/auth), this is intentional as authentication could either be
handled by this service or a 3rd party system or another system on the platform. [Mail](./app/services/mail) contains
the wrapper services that contain the code to send out emails. These wrapper services extend
the [email_service class](./app/services/mail/email_service.py) to ensure that functionality is common across new 3rd
party services that may be added. Currently, the services include SMTP, SendGrid & MailChimp, however, these are not
limiting & more could be added based on the needs of the system or which email provider is chosen. The default to use is
SMTP, but in case that fails, it defaults to a 3rd party.

## Deployment

Application has been built to allow for packaging into a container(a self contained application). This is made possible
using [Docker](https://www.docker.com/). This allows the application to be built and run in any environment
independently with very few external dependencies & deployed to any environment that supports Container runtime. Note
that this is not the only limitation as it can be deployed without the need for Docker.

To run the application in a docker container use the below commands:

`docker build -t <NAME_OF_IMAGE>:<VERSION> .`
OR
`docker build -t <NAME_OF_IMAGE>:<VERSION> -f Dockerfile`

First build the image and tag it with a name, the suffix is optional, notice the dot (.)

Then now you can run the application in the container and expose ports to the host

`docker run -it -p <HOST_PORT>:4000 <NAME_OF_IMAGE>`
Run the application container binding the container port to a host port.

The host port can be whatever you like as long as it is not a reserved host port (e.g, running linux services, if on
Linux). However, the container port (6000) is a must as the container exposes that port (This can be changed from
the [Dockerfile](./Dockerfile))

Ideally, this will be a representation of what will run in production in a single container(pod) in a kubernetes
cluster.

And of course ensure that the environment has the available environment variables so that the application can use them
as needed.
