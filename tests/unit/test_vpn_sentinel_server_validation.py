from vpn_sentinel_common.validation import (
    validate_client_id,
    validate_public_ip,
    validate_location_string,
    get_client_ip,
)
from flask import Flask


def test_validate_client_id_basic():
    assert validate_client_id('office-vpn-primary') == 'office-vpn-primary'
    assert validate_client_id('') == 'unknown'
    assert validate_client_id('a'*101) == 'unknown'
    assert validate_client_id('bad id!') == 'unknown'


def test_validate_public_ip():
    assert validate_public_ip('127.0.0.1') == '127.0.0.1'
    assert validate_public_ip('::1') == '::1'
    assert validate_public_ip('256.256.256.256') == 'unknown'
    assert validate_public_ip(None) == 'unknown'


def test_validate_location_string():
    assert validate_location_string('Bucharest', 'city') == 'Bucharest'
    assert validate_location_string('America/New_York', 'timezone') == 'America/New_York'
    assert validate_location_string('<script>', 'city') == 'Unknown'


def test_get_client_ip_from_headers():
    app = Flask(__name__)
    with app.test_request_context('/', headers={'X-Forwarded-For': '1.2.3.4, 5.6.7.8'}):
        assert get_client_ip() == '1.2.3.4'
