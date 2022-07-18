from typing import List
import smtplib
import ssl

from app.config import config
from app.logger import log
from app.utils import singleton


@singleton
class SmtpServer(object):
    context = ssl.create_default_context()
    server = smtplib.SMTP(host=config.mail_server, port=config.mail_port)

    def __int__(self, host: str, port: str):
        if config.mail_use_ssl:
            self.server = smtplib.SMTP_SSL(host=config.mail_server, port=config.mail_port, context=self.context)

    # @staticmethod
    def login(self, username: str, password: str):
        log.info(f"Logging into SMTP")
        try:
            self.server.ehlo()
            if config.mail_use_tls:
                self.server.starttls(context=self.context)
                self.server.login(user=username, password=password)
            if config.mail_use_ssl:
                self.server.login(user=config.mail_username, password=config.mail_password)
            self.server.ehlo()
        except Exception as e:
            log.error(f"Failed to login {e}")
            self.server.quit()

    def logout(self):
        log.info(f"Logging out of SMTP")
        try:
            self.server.quit()
        except Exception as e:
            log.error(f"Failed to quite smtp server {e}")
            self.server.quit()

    def sendmail(self, sender: str, recipients: List[str], message: str):
        try:
            if not self.__check_connection():
                self.server.connect(host=config.mail_server, port=config.mail_port)
            self.server.sendmail(from_addr=sender, to_addrs=recipients, msg=message)
        except Exception as e:
            log.error(f"Failed to send email {e}")

    def __check_connection(self) -> bool:
        try:
            status = self.server.noop()[0]
        except Exception as e:
            log.error(f"SMTP Server is disconnected {e}")
            status = -1
        return status == 250
