import tempfile

from test_helpers.utils import failing_task

from inspect_ai import eval, eval_retry
from inspect_ai.log import list_eval_logs, retryable_eval_logs
from inspect_ai._util.retry import httpx_should_retry, log_rate_limit_retry, log_retry_attempt, is_httpx_connection_error
from httpx import HTTPStatusError, ConnectTimeout, ConnectError, ReadTimeout
import logging


def test_eval_retry():
    # run eval with a solver that fails 2/3 times
    log = eval(failing_task, limit=1, model="mockllm/model")[0]

    # note the task id so we can be certain it remains the same
    task_id = log.eval.task_id

    # retry until we succeed (confirming the task_id is stable)
    while log.status != "success":
        log = eval_retry(log)[0]
        assert log.eval.task_id == task_id


def test_eval_retryable():
    with tempfile.TemporaryDirectory() as log_dir:
        # run eval with a solver that fails 2/3 of the time
        log = eval(tasks=failing_task, limit=1, model="mockllm/model", log_dir=log_dir)[
            0
        ]

        # note the task id so we can be certain it remains the same
        task_id = log.eval.task_id

        # retry until we succeed (confirming the task_id is stable)
        retryable = retryable_eval_logs(list_eval_logs(log_dir))
        while len(retryable) > 0:
            assert len(retryable) == 1
            assert retryable[0].task_id == task_id
            eval_retry(retryable, log_dir=log_dir)
            retryable = retryable_eval_logs(list_eval_logs(log_dir))

import pytest

class DummyRetryCallState:
    """A dummy retry state to simulate tenacity.RetryCallState for testing logging output."""
    def __init__(self, attempt_number, idle_for):
        self.attempt_number = attempt_number
        self.idle_for = idle_for

def test_httpx_should_retry_http_status_error():
    """Test retry behavior for HTTPStatusError based on various status codes."""
    # Define a dummy response object to simulate httpx's response
    class DummyResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    def make_http_status_error(code):
        response = DummyResponse(code)
        # Pass None for request. It is not needed for our test.
        return HTTPStatusError("error", request=None, response=response)

    # Status codes that should trigger a retry (408, 409, 429, and any 5xx errors)
    for code in [408, 409, 429, 500, 503]:
        err = make_http_status_error(code)
        assert httpx_should_retry(err) is True, f"Expected retry for status code {code}"

    # Other status codes should not trigger a retry (e.g., 400, 404)
    for code in [400, 404]:
        err = make_http_status_error(code)
        assert httpx_should_retry(err) is False, f"Expected no retry for status code {code}"

def test_httpx_should_retry_connection_error():
    """Test that connection-related exceptions are retried."""
    # Test with ConnectTimeout, ConnectError, ConnectionError, and ReadTimeout
    for ex in [ConnectTimeout("timeout"), ConnectError("connect error"), ConnectionError("conn error"), ReadTimeout("read timeout")]:
        assert httpx_should_retry(ex) is True, f"Expected retry for exception {ex}"

def test_httpx_should_retry_non_retry_exception():
    """Test that non-retryable exceptions do not trigger a retry."""
    ex = Exception("non retryable")
    assert httpx_should_retry(ex) is False

def test_log_rate_limit_retry(caplog):
    """Test logging output for rate limit retry attempts."""
    dummy_state = DummyRetryCallState(attempt_number=2, idle_for=0.5)
    context = "rate limit"
    with caplog.at_level(logging.DEBUG):
        log_rate_limit_retry(context, dummy_state)
    expected_message = f"{context} rate limit retry {dummy_state.attempt_number} after waiting for {dummy_state.idle_for}"
    logs = [record.message for record in caplog.records]
    assert any(expected_message in msg for msg in logs), "Expected log message not found."

def test_log_retry_attempt(caplog):
    """Test that the retry attempt logging function logs messages correctly."""
    dummy_state = DummyRetryCallState(attempt_number=4, idle_for=1.0)
    context = "connection"
    log_attempt = log_retry_attempt(context)
    with caplog.at_level(logging.DEBUG):
        log_attempt(dummy_state)
    expected_message = f"{context} connection retry {dummy_state.attempt_number} after waiting for {dummy_state.idle_for}"
    logs = [record.message for record in caplog.records]
    assert any(expected_message in msg for msg in logs), "Expected log message not found."

def test_is_httpx_connection_error():
    """Test is_httpx_connection_error for valid connection errors and non-errors."""
    # Should return True for connection error instances
    for ex in [ConnectTimeout("timeout"), ConnectError("connect error"), ConnectionError("conn"), ReadTimeout("read timeout")]:
        assert is_httpx_connection_error(ex) is True, f"Expected True for {ex}"
    # For any other exception, it should return False.
    assert is_httpx_connection_error(Exception("other")) is False
def test_httpx_should_retry_custom_http_status_error():
    """Test that a custom subclass of HTTPStatusError is handled correctly."""
    class CustomHTTPStatusError(HTTPStatusError):
        pass

    class DummyResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    def make_custom_error(code):
        response = DummyResponse(code)
        return CustomHTTPStatusError("custom error", request=None, response=response)

    # Test codes requiring retry
    for code in [408, 409, 429, 500, 503]:
        err = make_custom_error(code)
        assert httpx_should_retry(err) is True, f"Expected retry for custom error with status {code}"

    # Test codes that should not trigger a retry
    for code in [400, 404]:
        err = make_custom_error(code)
        assert httpx_should_retry(err) is False, f"Expected no retry for custom error with status {code}"

def test_is_httpx_connection_error_subclass():
    """Test that is_httpx_connection_error works correctly with a subclass of a connection error."""
    class CustomConnectTimeout(ConnectTimeout):
        pass

    custom_ex = CustomConnectTimeout("custom timeout")
    assert is_httpx_connection_error(custom_ex) is True, "Expected True for a custom ConnectTimeout subclass"

def test_log_retry_attempt_multiple(caplog):
    """Test that log_retry_attempt correctly logs multiple retry attempts."""
    # Create several dummy retry call states
    dummy_states = [DummyRetryCallState(attempt_number=i, idle_for=i*0.1) for i in range(1, 6)]
    context = "multi attempt"
    log_attempt = log_retry_attempt(context)

    with caplog.at_level(logging.DEBUG):
        for state in dummy_states:
            log_attempt(state)

    # Verify each expected log message is present
    for state in dummy_states:
        expected_message = f"{context} connection retry {state.attempt_number} after waiting for {state.idle_for}"
        assert expected_message in caplog.text, f"Expected log message not found for attempt {state.attempt_number}"

def test_log_rate_limit_retry_multiple(caplog):
    """Test that log_rate_limit_retry correctly logs multiple rate limit retry attempts."""
    dummy_states = [DummyRetryCallState(attempt_number=i, idle_for=i*0.2) for i in range(1, 4)]
    context = "rate limit multiple"

    with caplog.at_level(logging.DEBUG):
        for state in dummy_states:
            log_rate_limit_retry(context, state)

    # Verify that each expected log message exists in the log
    for state in dummy_states:
        expected_message = f"{context} rate limit retry {state.attempt_number} after waiting for {state.idle_for}"
        assert expected_message in caplog.text, f"Expected log message not found for rate limit attempt {state.attempt_number}"
def test_httpx_should_retry_unexpected_exception():
    """Test that an unexpected exception type does not trigger a retry."""
    ex = ValueError("unexpected error")
    assert httpx_should_retry(ex) is False

def test_log_retry_attempt_edge_case(caplog):
    """Test log_retry_attempt with edge case values (attempt_number = 0, idle_for = 0)."""
    dummy_state = DummyRetryCallState(attempt_number=0, idle_for=0)
    context = "edge case"
    log_attempt = log_retry_attempt(context)
    with caplog.at_level(logging.DEBUG):
        log_attempt(dummy_state)
    expected_message = f"{context} connection retry {dummy_state.attempt_number} after waiting for {dummy_state.idle_for}"
    logs = [record.message for record in caplog.records]
    assert any(expected_message in msg for msg in logs), "Expected edge case log message not found."

def test_log_rate_limit_retry_edge_case(caplog):
    """Test log_rate_limit_retry with edge case values (attempt_number = -1, idle_for = 0)."""
    dummy_state = DummyRetryCallState(attempt_number=-1, idle_for=0)
    context = "edge rate limit"
    with caplog.at_level(logging.DEBUG):
        log_rate_limit_retry(context, dummy_state)
    expected_message = f"{context} rate limit retry {dummy_state.attempt_number} after waiting for {dummy_state.idle_for}"
    logs = [record.message for record in caplog.records]
    assert any(expected_message in msg for msg in logs), "Expected edge rate limit log message not found."