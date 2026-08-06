import pytest
from app.worker import queues


def test_barua_queue_dlx_points_to_error_exchange():
    args = queues.barua_queue.queue_arguments
    assert args is not None
    assert args.get('x-dead-letter-exchange') == queues.BARUA_ERROR_EXCHANGE_NAME
    assert args.get('x-dead-letter-routing-key') == queues.BARUA_ERROR_ROUTING_KEY_NAME


def test_barua_error_queue_has_no_dlx():
    # Some kombu versions expose queue_arguments as attribute, others as kwarg
    args = getattr(queues.barua_error_queue, 'queue_arguments', None)
    # Error queue should be the sink and not dead-letter to itself
    assert args in (None, {})
