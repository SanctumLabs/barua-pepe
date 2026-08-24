import pytest

from app.domain.entities.email_sender import EmailSender
from app.domain.entities.email_recipient import EmailRecipient
from app.domain.entities.email_request import EmailRequest


def make_email_request():
    sender = EmailSender(email="sender@example.com", name="Sender")
    recipient = EmailRecipient(email="recipient@example.com", name="Recipient")
    return EmailRequest(sender=sender, recipients=[recipient], ccs=None, bccs=None, subject="sub", message="msg", attachments=None)


def test_send_email_forwards_request_id(monkeypatch):
    """send_email should call mail_sending_task.apply_async with request_id forwarded"""
    called = {}

    def fake_apply_async(kwargs):
        called['kwargs'] = kwargs

    # monkeypatch the task object
    import app.tasks.mail_sending_task as mail_task_mod

    monkeypatch.setattr(mail_task_mod.mail_sending_task, 'apply_async', staticmethod(fake_apply_async))

    from app.domain.send_email import send_email

    req = make_email_request()
    send_email(req, request_id='trace-123')

    assert 'kwargs' in called
    assert called['kwargs'].get('request_id') == 'trace-123'
    assert 'data' in called['kwargs']


def test_mail_sending_task_forwards_request_id_to_error_task(monkeypatch):
    """When the send fails and retries are exhausted, mail_error_task.apply_async should be called with the original request_id."""
    # make send_plain_mail always raise
    import app.services.mail as mail_svc_mod

    def fake_send_plain_mail(data):
        raise Exception("simulated send failure")

    monkeypatch.setattr(mail_svc_mod, 'send_plain_mail', fake_send_plain_mail)

    # capture apply_async on error task
    import app.tasks.mail_error_task as error_mod

    called = {}

    def fake_error_apply_async(kwargs):
        called['kwargs'] = kwargs

    monkeypatch.setattr(error_mod.mail_error_task, 'apply_async', staticmethod(fake_error_apply_async))

    # Prepare dummy `self` with request.retries == max_retries so the task will route to error queue
    class DummyRequest:
        retries = 3
        id = 'celery-request-id'

    class DummySelf:
        request = DummyRequest()
        max_retries = 3

        def retry(self, *args, **kwargs):
            # Celery's retry raises to signal a retry; emulate that to stop execution
            raise RuntimeError('simulated-retry')

    from app.tasks.mail_sending_task import mail_sending_task

    data = {'sender': {'email': 's@e.com', 'name': 'S'}, 'recipients': [{'email': 'r@e.com', 'name': 'R'}], 'subject': 'sub', 'message': 'msg'}

    with pytest.raises(RuntimeError):
        # call the wrapped function implementation directly; the task is defined as a bound function
        mail_sending_task.__wrapped__(DummySelf(), data, request_id='trace-xyz')

    assert 'kwargs' in called, 'mail_error_task.apply_async was not called'
    assert called['kwargs'].get('request_id') == 'trace-xyz'
    assert 'data' in called['kwargs']
