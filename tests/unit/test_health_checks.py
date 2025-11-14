import types
import subprocess

from vpn_sentinel_common import health


def test_check_client_process_monkeypatch(monkeypatch):
    # simulate psutil not present and pgrep finding the process
    monkeypatch.setattr(health, 'psutil', None)

    class FakeCompleted:
        returncode = 0

    def fake_run(cmd, stdout, stderr):
        return FakeCompleted()

    monkeypatch.setattr(subprocess, 'run', fake_run)
    # Test with Python client (default behavior should find either)
    res = health.check_client_process()
    assert res == 'healthy'


def test_network_connectivity_monkeypatch(monkeypatch):
    # monkeypatch _http_get to return a truthy value
    monkeypatch.setattr(health, '_http_get', lambda url, timeout=5: 'ok')
    assert health.check_network_connectivity() == 'healthy'


def test_server_connectivity_not_configured(monkeypatch):
    monkeypatch.delenv('VPN_SENTINEL_URL', raising=False)
    assert health.check_server_connectivity('') == 'not_configured'


def test_check_dns_leak_detection(monkeypatch):
    monkeypatch.setattr(health, '_http_get', lambda url, timeout=5: None)
    assert health.check_dns_leak_detection() == 'unavailable'


def test_get_system_info(monkeypatch):
    # Force psutil to None and mock df output
    monkeypatch.setattr(health, 'psutil', None)

    def fake_check_output(cmd, text=True):
        return 'Use% /\n  42%\n'

    monkeypatch.setattr(subprocess, 'check_output', fake_check_output)
    info = health.get_system_info()
    assert 'memory_percent' in info
    assert 'disk_percent' in info