import time
from vpn_sentinel_common.log_utils import get_current_time, log_info, log_warn, log_error


def test_get_current_time_returns_datetime_like():
    t = get_current_time()
    assert hasattr(t, 'isoformat')


def test_log_functions_do_not_raise(capsys):
    # Ensure logging shims run without throwing
    log_info('test', 'info message')
    log_warn('test', 'warn message')
    log_error('test', 'error message')
    # capture output
    captured = capsys.readouterr()
    assert 'INFO' in captured.out or 'WARN' in captured.out or 'ERROR' in captured.out
