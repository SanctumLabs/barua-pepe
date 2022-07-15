import smtplib, ssl
from app.config import config
from app.logger import log

context = ssl.create_default_context()
server = smtplib.SMTP(config.mail_server, config.mail_port)


def login_to_smtp_server(username: str, password: str):
    log.info(f"Logging into SMTP")
    try:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(user=username, password=password)
    except Exception as e:
        log.error(f"Failed to login {e}")
    finally:
        server.quit()


def logout_from_smtp():
    log.info(f"Logging out of SMTP")
    try:
        server.quit()
    except Exception as e:
        log.error(f"Failed to login {e}")
    finally:
        server.quit()
