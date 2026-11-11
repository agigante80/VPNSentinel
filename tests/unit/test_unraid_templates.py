"""Guards over the Unraid Community Applications templates and Dockerfile labels (issue #133).

The templates in unraid/ are XML that Unraid renders as an install form. A typo there ships a
form that validates and then misbehaves: a secret shown in clear, a client left on its
`http://your-server-url:5000` fallback, a dashboard toggle the server never reads. These guards
parse the real files (xml.etree, no network) and check the facts the code depends on.

Six guards over one subject (a dict of file texts), with deliberately different scopes:
  meta        each template: Repository agigante80/..., non-empty Overview, TemplateURL equal to the
              raw `main` URL of its own file under unraid/ (the URL resolves only once the work is
              merged to main)
  variables   the Variable names of each template equal an explicit, hard-coded set (never derived
              from .env.example, which carries gluetun-only and dead names)
  secrets     VPN_SENTINEL_API_KEY (both templates) is Required, Mask and empty by default;
              TELEGRAM_BOT_TOKEN is Mask. An empty key runs the server with auth disabled
              (api_routes.py), so the template can only assert the attributes
  client      VPN_SENTINEL_URL is Required with an empty Default (otherwise the client keeps the
              `http://your-server-url:5000` fallback and never turns green), Network is none, ExtraParams
              joins a container namespace, and the Overview names FIREWALL_OUTBOUND_SUBNETS
  profile     ca_profile.xml parses and has a non-empty Profile
  labels      the server Dockerfile net.unraid.docker.webui equals the server template WebUI, both
              Dockerfiles carry the OCI source/description/licenses labels, and the client usage
              label names agigante80/vpn-sentinel-client
  hygiene     no template or profile contains a home path or a private address. The patterns are
              assembled from fragments because the pre-commit hook scans this file too.

Failure scenario for the client (a manual Unraid check, not testable here): when gluetun's
FIREWALL_OUTBOUND_SUBNETS does not cover the LAN subnet of VPN_SENTINEL_URL, the client logs
`Failed to send keepalive to <server_url>` (component `api`, client/__main__.py) on every cycle and no
card for its client ID appears on /dashboard.

icon        (issue #134) both Dockerfiles carry net.unraid.docker.icon, and both templates an <Icon>,
            each equal to the raw `main` URL of docs/images/icon-256.png, and that file exists

Guard rules (CLAUDE.md): every guard has a mutation test proving it red, each mutation asserts
every OTHER guard still passes (assert_only_guard_fails), and each selector is asserted to match
something.
"""

import ipaddress
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from test_release_workflow_guards import assert_only_guard_fails

REPO_ROOT = Path(__file__).resolve().parents[2]
UNRAID = REPO_ROOT / "unraid"
RAW_BASE = "https://raw.githubusercontent.com/agigante80/VPNSentinel/main/unraid/"
ICON_URL = "https://raw.githubusercontent.com/agigante80/VPNSentinel/main/docs/images/icon-256.png"
ICON_FILE = "docs/images/icon-256.png"

SERVER_XML = "vpn-sentinel-server.xml"
CLIENT_XML = "vpn-sentinel-client.xml"
PROFILE_XML = "ca_profile.xml"
SERVER_DOCKERFILE = "src/vpn_sentinel/server/Dockerfile"
CLIENT_DOCKERFILE = "src/vpn_sentinel/client/Dockerfile"

SERVER_VARS = {
    "VPN_SENTINEL_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "VPN_SENTINEL_API_PATH",
    "VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED",
    "TZ",
}
CLIENT_VARS = {
    "VPN_SENTINEL_URL",
    "VPN_SENTINEL_API_KEY",
    "VPN_SENTINEL_CLIENT_ID",
    "VPN_SENTINEL_API_PATH",
    "TZ",
}
OCI_LABELS = (
    "org.opencontainers.image.source",
    "org.opencontainers.image.description",
    "org.opencontainers.image.licenses",
)

# Built from fragments: this file is itself scanned by the pre-commit hook.
HOME_PATH = "/" + "home" + "/"
HOOK_PATTERN = re.compile(
    "("
    + "|".join(
        [HOME_PATH, "1" + "0" + r"\.", "192" + r"\." + "168" + r"\.", "172" + r"\.(1[6-9]|2[0-9]|3[0-1])" + r"\."]
    )
    + ")"
)
IPV4_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")

# ---------------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------------


def real_subject():
    return {
        SERVER_XML: (UNRAID / SERVER_XML).read_text(),
        CLIENT_XML: (UNRAID / CLIENT_XML).read_text(),
        PROFILE_XML: (UNRAID / PROFILE_XML).read_text(),
        SERVER_DOCKERFILE: (REPO_ROOT / SERVER_DOCKERFILE).read_text(),
        CLIENT_DOCKERFILE: (REPO_ROOT / CLIENT_DOCKERFILE).read_text(),
    }


def mutated(old, new, key):
    """The real subject with one replacement in file `key`. Asserts the anchor exists so a
    mutation can never test nothing."""
    subject = real_subject()
    assert old in subject[key], f"mutation anchor not found in {key}: {old!r}"
    subject[key] = subject[key].replace(old, new, 1)
    return subject


def config(root, name):
    """The Config element of a template whose Name attribute (the form label) is `name`, matched
    on Target, which is the variable name."""
    found = [c for c in root.iter("Config") if c.get("Target") == name and c.get("Type") == "Variable"]
    return found[0] if len(found) == 1 else None


def variable_names(root):
    return {c.get("Target") for c in root.iter("Config") if c.get("Type") == "Variable"}


def dockerfile_labels(text):
    """Keys of the LABEL instruction(s), with their quoted values."""
    labels = {}
    for block in re.findall(r"^LABEL\b(.*?)(?=^\S)", text + "\nEND", re.M | re.S):
        for key, value in re.findall(r'([\w.\-]+)="([^"]*)"', block):
            labels[key] = value
    return labels


# ---------------------------------------------------------------------------------
# Guards: take the subject, return a list of error strings (empty = pass)
# ---------------------------------------------------------------------------------


def _root(subject, key, errors):
    try:
        return ET.fromstring(subject[key])
    except ET.ParseError as exc:
        errors.append(f"{key} does not parse: {exc}")
        return None


def meta_errors(subject):
    errors = []
    for key in (SERVER_XML, CLIENT_XML):
        root = _root(subject, key, errors)
        if root is None:
            continue
        if not (root.findtext("Repository") or "").startswith("agigante80/"):
            errors.append(f"{key} Repository must start with agigante80/")
        if not (root.findtext("Overview") or "").strip():
            errors.append(f"{key} Overview is empty")
        if root.findtext("TemplateURL") != RAW_BASE + key:
            errors.append(f"{key} TemplateURL must be {RAW_BASE + key}")
    return errors


def variables_errors(subject):
    errors = []
    for key, expected in ((SERVER_XML, SERVER_VARS), (CLIENT_XML, CLIENT_VARS)):
        root = _root(subject, key, errors)
        if root is None:
            continue
        got = variable_names(root)
        if got != expected:
            errors.append(f"{key} variables differ: missing {sorted(expected - got)}, extra {sorted(got - expected)}")
    return errors


def secrets_errors(subject):
    errors = []
    for key in (SERVER_XML, CLIENT_XML):
        root = _root(subject, key, errors)
        if root is None:
            continue
        api_key = config(root, "VPN_SENTINEL_API_KEY")
        if api_key is None:
            errors.append(f"{key} has no VPN_SENTINEL_API_KEY variable")
        else:
            for attr in ("Required", "Mask"):
                if api_key.get(attr) != "true":
                    errors.append(f'{key} VPN_SENTINEL_API_KEY must have {attr}="true"')
            if api_key.get("Default") != "":
                errors.append(f"{key} VPN_SENTINEL_API_KEY must have an empty Default")
    server = _root(subject, SERVER_XML, errors)
    if server is not None:
        token = config(server, "TELEGRAM_BOT_TOKEN")
        if token is None or token.get("Mask") != "true":
            errors.append(f'{SERVER_XML} TELEGRAM_BOT_TOKEN must have Mask="true"')
    return errors


def client_errors(subject):
    errors = []
    root = _root(subject, CLIENT_XML, errors)
    if root is None:
        return errors
    url = config(root, "VPN_SENTINEL_URL")
    if url is None:
        errors.append("client has no VPN_SENTINEL_URL variable")
    else:
        if url.get("Required") != "true":
            errors.append('client VPN_SENTINEL_URL must have Required="true"')
        if url.get("Default") != "":
            errors.append(f"client VPN_SENTINEL_URL must have an empty Default, got {url.get('Default')!r}")
    if (root.findtext("Network") or "").strip() != "none":
        errors.append("client Network must be none")
    if "--network=container:" not in (root.findtext("ExtraParams") or ""):
        errors.append("client ExtraParams must contain --network=container:")
    if "FIREWALL_OUTBOUND_SUBNETS" not in (root.findtext("Overview") or ""):
        errors.append("client Overview must mention FIREWALL_OUTBOUND_SUBNETS")
    return errors


def profile_errors(subject):
    errors = []
    root = _root(subject, PROFILE_XML, errors)
    if root is not None:
        profile = root if root.tag == "Profile" else root.find(".//Profile")
        if profile is None or not ("".join(profile.itertext())).strip():
            errors.append("ca_profile.xml has no non-empty Profile")
    return errors


def labels_errors(subject):
    errors = []
    server = dockerfile_labels(subject[SERVER_DOCKERFILE])
    client = dockerfile_labels(subject[CLIENT_DOCKERFILE])
    root = _root(subject, SERVER_XML, errors)
    webui = root.findtext("WebUI") if root is not None else None
    if not webui:
        errors.append("server template has no WebUI")
    if server.get("net.unraid.docker.webui") != webui:
        errors.append(
            f"server Dockerfile net.unraid.docker.webui {server.get('net.unraid.docker.webui')!r} != {webui!r}"
        )
    for name, labels in (("server", server), ("client", client)):
        for label in OCI_LABELS:
            if not labels.get(label):
                errors.append(f"{name} Dockerfile lacks label {label}")
    if "agigante80/vpn-sentinel-client" not in client.get("usage", ""):
        errors.append("client usage label must name agigante80/vpn-sentinel-client")
    return errors


def icon_errors(subject):
    errors = []
    for key in (SERVER_DOCKERFILE, CLIENT_DOCKERFILE):
        got = dockerfile_labels(subject[key]).get("net.unraid.docker.icon")
        if got != ICON_URL:
            errors.append(f"{key} net.unraid.docker.icon {got!r} != {ICON_URL!r}")
    for key in (SERVER_XML, CLIENT_XML):
        root = _root(subject, key, errors)
        if root is not None and root.findtext("Icon") != ICON_URL:
            errors.append(f"{key} Icon {root.findtext('Icon')!r} != {ICON_URL!r}")
    if not (REPO_ROOT / ICON_FILE).is_file():
        errors.append(f"{ICON_FILE} does not exist, the icon URL would 404")
    return errors


def hygiene_errors(subject):
    errors = []
    for key in (SERVER_XML, CLIENT_XML, PROFILE_XML):
        text = subject[key]
        if HOOK_PATTERN.search(text):
            errors.append(f"{key} contains text the pre-commit hook rejects")
        for literal in IPV4_RE.findall(text):
            try:
                if ipaddress.ip_address(literal).is_private:
                    errors.append(f"{key} contains private address {literal}")
            except ValueError:
                pass
    return errors


GUARDS = {
    "meta": lambda s: not meta_errors(s),
    "variables": lambda s: not variables_errors(s),
    "secrets": lambda s: not secrets_errors(s),
    "client": lambda s: not client_errors(s),
    "profile": lambda s: not profile_errors(s),
    "labels": lambda s: not labels_errors(s),
    "icon": lambda s: not icon_errors(s),
    "hygiene": lambda s: not hygiene_errors(s),
}


def assert_guard(errors_fn, subject):
    errors = errors_fn(subject)
    assert not errors, "; ".join(errors)


# ---------------------------------------------------------------------------------
# Real files
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "errors_fn",
    [
        meta_errors,
        variables_errors,
        secrets_errors,
        client_errors,
        profile_errors,
        labels_errors,
        icon_errors,
        hygiene_errors,
    ],
)
def test_real_files_pass_every_guard(errors_fn):
    assert_guard(errors_fn, real_subject())


def test_selectors_match_something():
    subject = real_subject()
    server = ET.fromstring(subject[SERVER_XML])
    client = ET.fromstring(subject[CLIENT_XML])
    assert variable_names(server) and variable_names(client)
    assert config(server, "VPN_SENTINEL_API_KEY") is not None
    assert config(server, "TELEGRAM_BOT_TOKEN") is not None
    assert config(client, "VPN_SENTINEL_URL") is not None
    assert "net.unraid.docker.webui" in dockerfile_labels(subject[SERVER_DOCKERFILE])
    assert dockerfile_labels(subject[CLIENT_DOCKERFILE]).get("usage")


def test_icon_urls_point_at_the_committed_icon():
    subject = real_subject()
    assert ICON_URL.endswith("/" + ICON_FILE)
    for key in (SERVER_DOCKERFILE, CLIENT_DOCKERFILE):
        assert dockerfile_labels(subject[key])["net.unraid.docker.icon"] == ICON_URL
    for key in (SERVER_XML, CLIENT_XML):
        assert ET.fromstring(subject[key]).findtext("Icon") == ICON_URL


def test_server_webui_targets_the_dashboard_port_and_path():
    """8080 and /dashboard are what the server serves (server_utils.py, dashboard_routes.py)."""
    root = ET.fromstring(real_subject()[SERVER_XML])
    assert root.findtext("WebUI") == "http://[IP]:[PORT:8080]/dashboard"
    ports = {c.get("Target"): (c.get("Default"), c.text) for c in root.iter("Config") if c.get("Type") == "Port"}
    # Container ports the server listens on (server_utils.py defaults); host side defaults to the same.
    assert ports == {"5000": ("5000", "5000"), "8080": ("8080", "8080"), "8081": ("8081", "8081")}


def test_client_publishes_no_ports():
    root = ET.fromstring(real_subject()[CLIENT_XML])
    assert not [c for c in root.iter("Config") if c.get("Type") == "Port"]


# ---------------------------------------------------------------------------------
# Mutations: each guard is observed red, and no other guard fires
# ---------------------------------------------------------------------------------


def test_secrets_guard_negative_mask_removed():
    # The API key is the only Required variable of the server template.
    subject = mutated('Required="true" Mask="true"', 'Required="true" Mask="false"', SERVER_XML)
    with pytest.raises(AssertionError, match='VPN_SENTINEL_API_KEY must have Mask="true"'):
        assert_guard(secrets_errors, subject)
    assert_only_guard_fails(subject, "secrets", guards=GUARDS)


def test_secrets_guard_negative_api_key_default_not_empty():
    subject = mutated(
        'Target="VPN_SENTINEL_API_KEY" Default=""', 'Target="VPN_SENTINEL_API_KEY" Default="changeme"', SERVER_XML
    )
    with pytest.raises(AssertionError, match="VPN_SENTINEL_API_KEY must have an empty Default"):
        assert_guard(secrets_errors, subject)
    assert_only_guard_fails(subject, "secrets", guards=GUARDS)


def test_secrets_guard_negative_telegram_token_unmasked():
    # The token is the only optional (Required="false") masked variable.
    subject = mutated('Required="false" Mask="true"', 'Required="false" Mask="false"', SERVER_XML)
    with pytest.raises(AssertionError, match='TELEGRAM_BOT_TOKEN must have Mask="true"'):
        assert_guard(secrets_errors, subject)
    assert_only_guard_fails(subject, "secrets", guards=GUARDS)


def test_variables_guard_negative_wrong_dashboard_toggle_name():
    subject = mutated("VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED", "VPN_SENTINEL_SERVER_DASHBOARD_ENABLED", SERVER_XML)
    with pytest.raises(AssertionError, match="missing .*VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED"):
        assert_guard(variables_errors, subject)
    assert_only_guard_fails(subject, "variables", guards=GUARDS)


def test_client_guard_negative_url_keeps_fallback_default():
    subject = mutated(
        'Target="VPN_SENTINEL_URL" Default=""',
        'Target="VPN_SENTINEL_URL" Default="http://your-server-url:5000"',
        CLIENT_XML,
    )
    with pytest.raises(AssertionError, match="VPN_SENTINEL_URL must have an empty Default"):
        assert_guard(client_errors, subject)
    assert_only_guard_fails(subject, "client", guards=GUARDS)


def test_client_guard_negative_overview_drops_firewall_note():
    subject = mutated("FIREWALL_OUTBOUND_SUBNETS", "FIREWALL_SUBNETS", CLIENT_XML)
    with pytest.raises(AssertionError, match="Overview must mention FIREWALL_OUTBOUND_SUBNETS"):
        assert_guard(client_errors, subject)
    assert_only_guard_fails(subject, "client", guards=GUARDS)


def test_client_guard_negative_not_in_a_container_namespace():
    subject = mutated("<ExtraParams>--network=container:", "<ExtraParams>--network=host:", CLIENT_XML)
    with pytest.raises(AssertionError, match="ExtraParams must contain --network=container:"):
        assert_guard(client_errors, subject)
    assert_only_guard_fails(subject, "client", guards=GUARDS)


def test_labels_guard_negative_misspelled_webui_key():
    subject = mutated("net.unraid.docker.webui=", "net.unraid.docker.web-ui=", SERVER_DOCKERFILE)
    with pytest.raises(AssertionError, match="net.unraid.docker.webui None"):
        assert_guard(labels_errors, subject)
    assert_only_guard_fails(subject, "labels", guards=GUARDS)


def test_labels_guard_negative_stale_usage_label():
    subject = mutated("agigante80/vpn-sentinel-client", "vpn-sentinel/client", CLIENT_DOCKERFILE)
    with pytest.raises(AssertionError, match="usage label must name agigante80/vpn-sentinel-client"):
        assert_guard(labels_errors, subject)
    assert_only_guard_fails(subject, "labels", guards=GUARDS)


def test_labels_guard_negative_oci_label_missing():
    subject = mutated("org.opencontainers.image.licenses", "org.opencontainers.image.license", SERVER_DOCKERFILE)
    with pytest.raises(AssertionError, match="server Dockerfile lacks label org.opencontainers.image.licenses"):
        assert_guard(labels_errors, subject)
    assert_only_guard_fails(subject, "labels", guards=GUARDS)


def test_meta_guard_negative_template_url_points_at_another_file():
    subject = mutated(RAW_BASE + CLIENT_XML, RAW_BASE + SERVER_XML, CLIENT_XML)
    with pytest.raises(AssertionError, match="TemplateURL must be"):
        assert_guard(meta_errors, subject)
    assert_only_guard_fails(subject, "meta", guards=GUARDS)


def test_profile_guard_negative_empty_profile():
    subject = real_subject()
    subject[PROFILE_XML] = '<?xml version="1.0"?>\n<Profile></Profile>\n'
    with pytest.raises(AssertionError, match="no non-empty Profile"):
        assert_guard(profile_errors, subject)
    assert_only_guard_fails(subject, "profile", guards=GUARDS)


def test_hygiene_guard_negative_private_address_in_overview():
    private = ".".join(["192", "168", "1", "10"])
    subject = mutated("<Overview>", f"<Overview>Reach it at http://{private}:5000 ", CLIENT_XML)
    with pytest.raises(AssertionError, match="private address"):
        assert_guard(hygiene_errors, subject)
    assert_only_guard_fails(subject, "hygiene", guards=GUARDS)


def test_hygiene_guard_negative_home_path():
    subject = mutated("<Overview>", f"<Overview>See {HOME_PATH}me/x ", SERVER_XML)
    with pytest.raises(AssertionError, match="pre-commit hook rejects"):
        assert_guard(hygiene_errors, subject)
    # A home path trips only the hygiene guard (no IPv4 literal), like every other mutation.
    assert_only_guard_fails(subject, "hygiene", guards=GUARDS)


def test_icon_guard_negative_dockerfile_label_missing():
    subject = mutated("net.unraid.docker.icon", "net.unraid.docker.icons", SERVER_DOCKERFILE)
    with pytest.raises(AssertionError, match="net.unraid.docker.icon None"):
        assert_guard(icon_errors, subject)
    assert_only_guard_fails(subject, "icon", guards=GUARDS)


def test_icon_guard_negative_template_icon_points_at_another_branch():
    subject = mutated("/main/docs/images/icon-256.png", "/develop/docs/images/icon-256.png", CLIENT_XML)
    with pytest.raises(AssertionError, match="client.xml Icon"):
        assert_guard(icon_errors, subject)
    assert_only_guard_fails(subject, "icon", guards=GUARDS)
