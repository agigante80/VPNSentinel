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


def test_parse_dns_trace_cloudflare_format():
    """Test parsing Cloudflare whoami.cloudflare response format.
    
    Cloudflare returns a quoted string with space-separated key=value pairs.
    Example: "fl=922f1 ip=185.170.104.53 ts=1699651483.123 loc=PL colo=WAW"
    """
    # Real Cloudflare format with quotes
    cloudflare_response = '"fl=922f1 ip=185.170.104.53 ts=1699651483.123 loc=PL colo=WAW"'
    data = net.parse_dns_trace(cloudflare_response)
    assert data['loc'] == 'PL'
    assert data['colo'] == 'WAW'
    
    # Without quotes
    cloudflare_no_quotes = 'fl=abc ip=1.2.3.4 loc=US colo=LAX ts=123'
    data2 = net.parse_dns_trace(cloudflare_no_quotes)
    assert data2['loc'] == 'US'
    assert data2['colo'] == 'LAX'
    
    # Edge case: only some fields present
    partial = 'fl=xyz loc=GB'
    data3 = net.parse_dns_trace(partial)
    assert data3['loc'] == 'GB'
    assert data3['colo'] == ''  # Missing field should be empty
