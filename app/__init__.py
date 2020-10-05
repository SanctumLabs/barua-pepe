import logging
from flask import Flask, jsonify
from .config import config
import jinja2
from .logger import log as app_logger
from flask_mail import Mail
from celery import Celery
from kombu import Queue
import os
from .constants import EMAIL_DEFAULT_EXCHANGE, EMAIL_DEFAULT_QUEUE_NAME, EMAIL_DEFAULT_ROUTING_KEY, EMAIL_EXCHANGE, \
    EMAIL_QUEUE_NAME, EMAIL_ROUTING_KEY, EMAIL_ERROR_EXCHANGE, EMAIL_ERROR_ROUTING_KEY, EMAIL_ERROR_QUEUE_NAME

mail = Mail()

broker = os.environ.get("BROKER_URL", "amqp://")
result_backend = os.environ.get("RESULT_BACKEND", "rpc://")
result_backend_master = os.environ.get("RESULT_BACKEND_LEADER", "redismaster")

celery_app = Celery("EmailGateway", broker=broker, backend=result_backend, include=["app.tasks"])


class EmailGateway(Flask):
    """
     Custom application class subclassing Flask application. This is to ensure more modularity in
      terms of static files and templates. This way a module will have its own templates and the
       root template folder will be more modularized and easier to manage
     """

    def __init__(self):
        """
        jinja_loader object (a FileSystemLoader pointing to the global templates folder) is
        being replaced with a ChoiceLoader object that will first search the normal
        FileSystemLoader and then check a PrefixLoader that we create
        """
        Flask.__init__(self, __name__)
        self.jinja_loader = jinja2.ChoiceLoader(
            [self.jinja_loader, jinja2.PrefixLoader({}, delimiter=".")]
        )

    def register_blueprint(self, blueprint, **options):
        """
        Overriding to add the blueprints names to the prefix loader's mapping
        :param blueprint:
        :param options:
        """
        Flask.register_blueprint(self, blueprint, **options)
        self.jinja_loader.loaders[1].mapping[blueprint.name] = blueprint.jinja_loader


def create_app(config_name):
    """
    Creates a new flask app instance with the given configuration
    :param config_name: configuration to use when creating the application
    :return: a new WSGI Flask app
    :rtype: Flask
    """
    app = EmailGateway()

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    error_handlers(app)
    register_app_blueprints(app)
    app_logger_handler(app)
    request_handlers(app)

    mail.init_app(app)

    # Task Queues
    task_queues = (
        Queue(name=EMAIL_DEFAULT_QUEUE_NAME, routing_key=EMAIL_DEFAULT_ROUTING_KEY, exchange=EMAIL_DEFAULT_EXCHANGE),
        Queue(name=EMAIL_QUEUE_NAME, routing_key=EMAIL_ROUTING_KEY, exchange=EMAIL_EXCHANGE),
        Queue(name=EMAIL_ERROR_QUEUE_NAME, routing_key=EMAIL_ERROR_ROUTING_KEY, exchange=EMAIL_ERROR_EXCHANGE, queue_arguments={
            'x-message-ttl': 5000, # delay until the message is transferred in milliseconds
            'x-dead-letter-exchange': EMAIL_ERROR_EXCHANGE, # Exchange used to transfer the message from A to B.
            'x-dead-letter-routing-key': EMAIL_ERROR_ROUTING_KEY # Name of the queue we want the message transferred to.            
        })
    )

    # Task Routes
    task_routes = {
        "mail_sending_task": dict(
            queue=EMAIL_QUEUE_NAME
        ),
        "mail_error_task": dict(
            queue=EMAIL_ERROR_QUEUE_NAME
        )
    }

    result_backend_transport_options = {
        'master_name': result_backend_master,
        'retry_policy': {
            'timeout': 5.0
        }
    }

    # Set task routes and queues
    app.config.update(dict(
        task_protocol=1,
        task_default_queue=EMAIL_DEFAULT_QUEUE_NAME,
        task_default_exchange=EMAIL_DEFAULT_EXCHANGE,
        task_default_routing_key=EMAIL_DEFAULT_ROUTING_KEY,
        task_queues=task_queues,
        task_routes=task_routes,
        result_backend_transport_options=result_backend_transport_options,
    ))

    # Initialize celery application
    celery_app.conf.update(app.config)

    # this will reduce the load time for templates and increase the application performance
    app.jinja_env.cache = {}

    @app.route("/health")
    def health():
        return jsonify({"message": "I am healthy :D"}), 200

    return app


def request_handlers(app_):
    """
    Handles before and after the requests handled by the application
    :param app_: the current application
    """

    @app_.after_request
    def after_request(response):
        """
        Is handled afer each request and can be used to add headers to the response
        or handle further processing
        :param response: Response object that is sent back to client
        """
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


def app_logger_handler(app):
    """
    Will handle error logging for the application and will store the app log files in a file that can
    later be accessed.
    :param app: current flask application
    """

    if app.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


def error_handlers(app):
    """
    Error handlers function that will initialize error handling templates for the entire application
    :param app: the flask app
    """

    @app.errorhandler(404)
    def not_found(error):
        """
        This will handle errors that involve 404 messages
        :return: a template instructing user they have sent a request that does not exist on
         the server
        """
        app_logger.error(f"An error occurred during a request. Error => {error}")
        return jsonify(dict(message="Failed to find resource")), 404

    @app.errorhandler(500)
    def server_error(e):
        # Log the error and stacktrace.
        app_logger.error(f"An error occurred during a request. Error => {e}")
        return jsonify(dict(message=f"Request failed with error {e}")), 500

    @app.errorhandler(403)
    def error_403(error):
        app_logger.error(f"An error occurred during a request. Error => {error}")
        return jsonify(dict(message=f"Request failed with error {error}")), 403

    @app.errorhandler(400)
    def bad_request(error):
        app_logger.error(f"An error occurred during a request. Error => {error}")
        return jsonify(dict(message=f"Request failed with error {error}")), 400


def register_app_blueprints(app_):
    """
    Registers the application blueprints
    :param app_: the current flask app
    """
    from app.api import mail_api

    app_.register_blueprint(mail_api)
