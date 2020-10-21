from threading import Thread
from flask_mail import Message

from vantage6.server import app, mail, log


def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except ConnectionRefusedError as e:
            log.error("Mailserver error!")
            log.debug(e)


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(app, msg)).start()