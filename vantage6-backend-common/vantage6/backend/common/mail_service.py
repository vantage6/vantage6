import logging

from threading import Thread
from flask_mail import Message, Mail
from flask import Flask

from vantage6.common import logger_name

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class MailService:
    """
    Send emails from the service email account

    Parameters
    ----------
    app: flask.Flask
        The vantage6 flask application
    """

    def __init__(self, app: Flask) -> None:
        self.app = app
        self.mail = Mail(app)

    def _send_async_email(self, app: Flask, msg: Message) -> None:
        """
        Send email asynchronously

        Parameters
        ----------
        app: flask.Flask
            A vantage6 flask application
        msg: flask_mail.Message
            Message to send in the email
        """
        with app.app_context():
            try:
                self.mail.send(msg)
            except Exception as e:
                log.error("Mailserver error!")
                log.exception(e)

    def send_email(
        self,
        subject: str,
        sender: str,
        recipients: list[str],
        text_body: str,
        html_body: str,
    ) -> None:
        """
        Send an email.

        This is used for service emails, e.g. to help users reset their
        password.

        Parameters
        ----------
        subject: str
            Subject of the email
        sender: str
            Email address of the sender
        recipients: List[str]
            List of email addresses of recipients
        text_body: str
            Email body in plain text
        html_body: str
            Email body in HTML
        """
        msg = Message(subject, sender=sender, recipients=recipients)
        msg.body = text_body
        msg.html = html_body
        Thread(target=self._send_async_email, args=(self.app, msg)).start()
