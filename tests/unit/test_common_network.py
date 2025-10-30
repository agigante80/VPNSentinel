from vpn_sentinel_common.network import parse_geolocation, parse_dns_trace


def test_parse_geolocation_empty():
    res = parse_geolocation('')
    assert isinstance(res, dict)
    assert res.get('ip', '') == ''


def test_parse_dns_trace():
    text = 'loc=us-east\ncolo=abc123\n'
    res = parse_dns_trace(text)
    assert res['loc'] == 'us-east'
    assert res['colo'] == 'abc123'
