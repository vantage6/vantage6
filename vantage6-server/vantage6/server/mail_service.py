import logging

from threading import Thread
from flask_mail import Message

from vantage6.common import logger_name


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class MailService:

    def __init__(self, app, mail):
        self.app = app
        self.mail = mail

    def send_async_email(self, app, msg):
        with app.app_context():
            try:
                self.mail.send(msg)
            except ConnectionRefusedError as e:
                log.error("Mailserver error!")
                log.debug(e)

    def send_email(self, subject, sender, recipients, text_body, html_body):
        msg = Message(subject, sender=sender, recipients=recipients)
        msg.body = text_body
        msg.html = html_body
        Thread(target=self.send_async_email, args=(self.app, msg)).start()
