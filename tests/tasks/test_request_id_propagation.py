import pytest

from app.domain.entities.email_sender import EmailSender
from app.domain.entities.email_recipient import EmailRecipient
from app.domain.entities.email_request import EmailRequest


def make_email_request():
    sender = EmailSender(email="sender@example.com", name="Sender")
    recipient = EmailRecipient(email="recipient@example.com", name="Recipient")
    return EmailRequest(sender=sender, recipients=[recipient], ccs=None, bccs=None, subject="sub", message="msg", attachments=None)


def test_celery_email_dispatcher_forwards_request_id(monkeypatch):
    """Celery adapter forwards the request ID and serialized request."""
    from app.infra.adapters.celery_email_dispatcher import CeleryEmailDispatcher

    called = {}

    def fake_apply_async(kwargs):
        called["kwargs"] = kwargs

    import app.infra.adapters.celery_email_dispatcher as dispatcher_module

    monkeypatch.setattr(
        dispatcher_module.mail_sending_task, "apply_async", fake_apply_async
    )

    request = make_email_request()
    CeleryEmailDispatcher().dispatch(request, request_id="trace-123")

    assert called["kwargs"] == {
        "data": request.to_task_payload(),
        "request_id": "trace-123",
    }


def test_mail_sending_task_forwards_request_id_to_error_task(monkeypatch):
    """When the send fails and retries are exhausted, mail_error_task.apply_async should be called with the original request_id."""
    # make send_plain_mail always raise
    import app.tasks.mail_sending_task as mail_task_mod

    def fake_send_plain_mail(data):
        raise Exception("simulated send failure")

    monkeypatch.setattr(mail_task_mod, 'send_plain_mail', fake_send_plain_mail)

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
        mail_sending_task.run.__func__(DummySelf(), data, request_id='trace-xyz')

    assert 'kwargs' in called, 'mail_error_task.apply_async was not called'
    assert called['kwargs'].get('request_id') == 'trace-xyz'
    assert 'data' in called['kwargs']
