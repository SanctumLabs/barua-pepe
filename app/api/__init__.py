# flake8: noqa
from flask import Blueprint

mail_api = Blueprint(
    name="MailApi",
    import_name=__name__,
    url_prefix=f"/api/v1/mail",
    static_folder="static",
    template_folder="templates",
)

from . import rest_api
