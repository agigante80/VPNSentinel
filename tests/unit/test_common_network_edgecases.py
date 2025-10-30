import json

from vpn_sentinel_common import network as net


def test_parse_geolocation_empty_and_ipapi():
    empty = net.parse_geolocation('', source='ipinfo.io')
    assert empty['ip'] == '' and empty['country'] == ''

    ipapi = '{"query":"1.2.3.4","countryCode":"US","city":"Test","regionName":"Some","isp":"ISP","timezone":"UTC"}'
    parsed = net.parse_geolocation(ipapi, source='ip-api.com')
    assert parsed['ip'] == '1.2.3.4'
    assert parsed['country'] == 'US'


def test_parse_dns_trace_variants():
    trace = 'loc=NY\ncolo=nyc1\n'
    parsed = net.parse_dns_trace(trace)
    assert parsed['loc'] == 'NY'
    assert parsed['colo'] == 'nyc1'

    parsed_empty = net.parse_dns_trace('')
    assert parsed_empty['loc'] == '' and parsed_empty['colo'] == ''


def test_network_cli_geolocation(tmp_path, monkeypatch):
    # run the client shim CLI with sample input
    from subprocess import Popen, PIPE
    from pathlib import Path

    sample = '{"ip":"8.8.8.8","country":"US","city":"Mountain View","region":"CA","org":"Google","timezone":"PST"}'
    # Find vpn-sentinel-client/lib/network.py by walking up parent directories
    p = Path(__file__).resolve()
    script = None
    for parent in [p] + list(p.parents):
        candidate = parent / 'vpn-sentinel-client' / 'lib' / 'network.py'
        if candidate.exists():
            script = str(candidate)
            break
    assert script is not None, 'Could not find vpn-sentinel-client/lib/network.py from test location'
    p = Popen(['python3', script], stdin=PIPE, stdout=PIPE)
    out, _ = p.communicate(sample.encode())
    data = json.loads(out.decode())
    assert data['ip'] == '8.8.8.8'


def test_network_cli_dns(tmp_path):
    from subprocess import Popen, PIPE
    from pathlib import Path

    sample = 'loc=LA\ncolo=la1\n'
    p = Path(__file__).resolve()
    script = None
    for parent in [p] + list(p.parents):
        candidate = parent / 'vpn-sentinel-client' / 'lib' / 'network.py'
        if candidate.exists():
            script = str(candidate)
            break
    assert script is not None, 'Could not find vpn-sentinel-client/lib/network.py from test location'
    p = Popen(['python3', script, '--dns'], stdin=PIPE, stdout=PIPE)
    out, _ = p.communicate(sample.encode())
    data = json.loads(out.decode())
    assert data['loc'] == 'LA'
    assert data['colo'] == 'la1'
