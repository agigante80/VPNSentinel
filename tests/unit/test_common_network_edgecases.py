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

    sample = '{"ip":"8.8.8.8","country":"US","city":"Mountain View","region":"CA","org":"Google","timezone":"PST"}'
    p = Popen(['python3', 'vpn-sentinel-client/lib/network.py'], stdin=PIPE, stdout=PIPE)
    out, _ = p.communicate(sample.encode())
    data = json.loads(out.decode())
    assert data['ip'] == '8.8.8.8'


def test_network_cli_dns(tmp_path):
    from subprocess import Popen, PIPE

    sample = 'loc=LA\ncolo=la1\n'
    p = Popen(['python3', 'vpn-sentinel-client/lib/network.py', '--dns'], stdin=PIPE, stdout=PIPE)
    out, _ = p.communicate(sample.encode())
    data = json.loads(out.decode())
    assert data['loc'] == 'LA'
    assert data['colo'] == 'la1'
