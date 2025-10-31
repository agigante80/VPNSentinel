import json

from vpn_sentinel_common import network as net


def test_parse_geolocation_empty_and_ipapi():
    empty = net.parse_geolocation('', source='ipinfo.io')
    # canonical implementation returns empty or 'unknown' values for missing fields
    assert empty.get('ip', '') in (None, '', 'unknown')
    assert empty.get('country', '') in (None, '', 'Unknown')

    ipapi = '{"query":"1.2.3.4","countryCode":"US","city":"Test","regionName":"Some","isp":"ISP","timezone":"UTC"}'
    parsed = net.parse_geolocation(ipapi, source='ip-api.com')
    assert parsed['ip'] == '1.2.3.4'
    assert parsed['country'] == 'US'


def test_parse_dns_trace_variants():
    trace = """loc=NY
colo=nyc1
"""
    parsed = net.parse_dns_trace(trace)
    assert parsed['loc'] == 'NY'
    assert parsed['colo'] == 'nyc1'

    parsed_empty = net.parse_dns_trace('')
    # canonical implementation may return empty strings or an empty dict
    assert (parsed_empty.get('loc', '') in ('', None))
    assert (parsed_empty.get('colo', '') in ('', None))


def test_parse_geolocation_via_api_input():
    sample = '{"ip":"8.8.8.8","country":"US","city":"Mountain View","region":"CA","org":"Google","timezone":"PST"}'
    data = net.parse_geolocation(sample)
    assert data['ip'] == '8.8.8.8'


def test_parse_dns_trace_direct_call():
    sample = """loc=LA
colo=la1
"""
    data = net.parse_dns_trace(sample)
    assert data['loc'] == 'LA'
    assert data['colo'] == 'la1'
