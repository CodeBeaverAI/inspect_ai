import pytest
from rich.text import Text
from inspect_ai._display.core import footer

def test_task_http_rate_limits(monkeypatch):
    """Test task_http_rate_limits returns expected HTTP rate limits."""
    monkeypatch.setattr(footer, 'http_rate_limit_count', lambda: 1000)
    result = footer.task_http_rate_limits()
    assert result == {"HTTP rate limits": "1,000"}

def test_task_http_rate_limits_str(monkeypatch):
    """Test task_http_rate_limits_str returns correct formatted string."""
    monkeypatch.setattr(footer, 'http_rate_limit_count', lambda: 500)
    result = footer.task_http_rate_limits_str()
    assert result == "HTTP rate limits: 500"

def test_task_resources(monkeypatch):
    """Test task_resources correctly aggregates concurrency status data."""
    dummy_status = {"modelA": (1, 4), "modelB": (2, 8)}
    monkeypatch.setattr(footer, 'concurrency_status', lambda: dummy_status)
    # Override task_dict to act as an identity function for testing
    monkeypatch.setattr(footer, 'task_dict', lambda d: d)
    result = footer.task_resources()
    expected = {"modelA": "1/4", "modelB": "2/8"}
    assert result == expected

def test_task_counters(monkeypatch):
    """Test task_counters merges given counters with HTTP rate limits."""
    counters = {"test": "value"}
    monkeypatch.setattr(footer, 'task_http_rate_limits', lambda: {"HTTP rate limits": "999"})
    # Override task_dict to act as an identity function for testing
    monkeypatch.setattr(footer, 'task_dict', lambda d: d)
    result = footer.task_counters(counters)
    expected = {"test": "value", "HTTP rate limits": "999"}
    assert result == expected

def test_task_footer(monkeypatch):
    """Test task_footer returns a tuple of Text objects with correct markup and style."""
    # Monkeypatch internal functions to return fixed strings
    monkeypatch.setattr(footer, 'task_resources', lambda: "resources_marked")
    monkeypatch.setattr(footer, 'task_counters', lambda counters: "counters_marked")
    counters = {"dummy": "data"}
    result = footer.task_footer(counters, style="bold")
    # Check result type and length
    assert isinstance(result, tuple)
    assert len(result) == 2
    # Check that each element is a Rich Text object
    assert isinstance(result[0], Text)
    assert isinstance(result[1], Text)
    # Confirm that the style is applied
    assert "bold" in result[0].style
    assert "bold" in result[1].style
    # Verify that the markup text is set correctly by comparing plain text
    assert result[0].plain == "resources_marked"
    assert result[1].plain == "counters_marked"
def test_task_counters_override(monkeypatch):
    """Test task_counters properly overrides the HTTP rate limits key if provided in counters."""
    counters = {"HTTP rate limits": "user_value", "other": "123"}
    # Override task_http_rate_limits to return a specific value
    monkeypatch.setattr(footer, 'task_http_rate_limits', lambda: {"HTTP rate limits": "test_value"})
    # Override task_dict to be an identity function for testing
    monkeypatch.setattr(footer, 'task_dict', lambda d: d)
    result = footer.task_counters(counters)
    # The HTTP rate limits value from task_http_rate_limits should override 'user_value'
    expected = {"HTTP rate limits": "test_value", "other": "123"}
    assert result == expected

def test_task_resources_empty(monkeypatch):
    """Test task_resources returns an empty dictionary when concurrency_status is empty."""
    monkeypatch.setattr(footer, 'concurrency_status', lambda: {})
    monkeypatch.setattr(footer, 'task_dict', lambda d: d)
    result = footer.task_resources()
    expected = {}
    assert result == expected

def test_task_counters_empty(monkeypatch):
    """Test task_counters returns only HTTP rate limits when counters is an empty dict."""
    monkeypatch.setattr(footer, 'task_http_rate_limits', lambda: {"HTTP rate limits": "999"})
    monkeypatch.setattr(footer, 'task_dict', lambda d: d)
    result = footer.task_counters({})
    expected = {"HTTP rate limits": "999"}
    assert result == expected

def test_task_footer_default_style(monkeypatch):
    monkeypatch.setattr(footer, 'task_footer', footer.task_footer.__wrapped__)
    """Test task_footer returns Rich Text objects with default (empty) style when no style passed."""
    # Override internal functions to return fixed strings
    monkeypatch.setattr(footer, 'task_resources', lambda: "default_resources")
    monkeypatch.setattr(footer, 'task_counters', lambda counters: "default_counters")
    counters = {"dummy": "data"}
    result = footer.task_footer(counters)
    # Check result type and length, and that style is empty (default)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], Text)
    assert isinstance(result[1], Text)
    # Since no style is provided, the style attribute should be an empty string
    assert result[0].style == "" or result[0].style is None or "default" in result[0].style
    assert result[1].style == "" or result[1].style is None or "default" in result[1].style
    # Verify that the markup text is set correctly by comparing plain text
    assert result[0].plain == "default_resources"
    assert result[1].plain == "default_counters"
def test_task_footer_is_throttled():
    """Test that the task_footer function is decorated with throttle by checking for __wrapped__ attribute."""
    assert hasattr(footer.task_footer, "__wrapped__")

def test_task_http_rate_limits_zero(monkeypatch):
    """Test task_http_rate_limits returns correct output when http_rate_limit_count returns 0."""
    monkeypatch.setattr(footer, 'http_rate_limit_count', lambda: 0)
    result = footer.task_http_rate_limits()
    assert result == {"HTTP rate limits": "0"}

def test_task_http_rate_limits_str_large(monkeypatch):
    """Test task_http_rate_limits_str returns correctly formatted string for large numbers."""
    monkeypatch.setattr(footer, 'http_rate_limit_count', lambda: 1234567)
    result = footer.task_http_rate_limits_str()
    assert result == "HTTP rate limits: 1,234,567"

def test_task_resources_format(monkeypatch):
    """Test task_resources returns a custom formatted string when task_dict is formatted differently."""
    dummy_status = {"modelX": (3, 10), "modelY": (5, 15)}
    monkeypatch.setattr(footer, 'concurrency_status', lambda: dummy_status)
    monkeypatch.setattr(footer, 'task_dict', lambda d: ", ".join(f"{k}={v}" for k, v in d.items()))
    result = footer.task_resources()
    expected_str = "modelX=3/10, modelY=5/15"
    assert result == expected_str

def test_task_counters_format(monkeypatch):
    """Test task_counters returns a custom formatted string when task_dict is formatted differently."""
    counters = {"key1": "val1"}
    monkeypatch.setattr(footer, 'task_http_rate_limits', lambda: {"HTTP rate limits": "888"})
    monkeypatch.setattr(footer, 'task_dict', lambda d: ";".join(f"{k}:{v}" for k, v in d.items()))
    result = footer.task_counters(counters)
    expected_str = "key1:val1;HTTP rate limits:888"
    assert result == expected_str