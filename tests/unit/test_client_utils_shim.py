from vpn_sentinel_common.utils import sanitize_string, json_escape


def test_utils_shim_cli_sanitize():
    # Directly call the canonical helper instead of invoking a wrapper script.
    # Avoid NUL (\x00) in argv — use 0x1f control char which is safe and verifies
    # stripping of control characters.
    result = sanitize_string('a\x1fb')
    assert result == 'ab'


def test_utils_shim_cli_escape():
    raw = 'a"b\\c'
    expected = raw.replace('\\', '\\\\').replace('"', '\\"')
    assert json_escape(raw) == expected
