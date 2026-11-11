"""Structural guards over the shipped compose files (issue #129).

The root compose.yaml (the README Quick Start) once shipped unpullable images and a
client outside the VPN network namespace, and `docker compose config --quiet` still
passed. These guards read the RESOLVED configuration, exactly as Docker applies it
(defaults, the file's own .env.example, interpolation), via

    docker compose --env-file <env> --profile '*' -f <compose> config --format json

`--profile '*'` is required: without it Compose omits profile-gated services. The
resolved output is never committed (it embeds absolute host paths).

Three guards, with deliberately different scopes:
  image         every shipped compose file: VPNSentinel images are agigante80/vpn-sentinel-*:<tag>
  namespace     files running gluetun + the sentinel client (ROOT, ALL_IN_ONE, CLIENT_WITH_VPN):
                client uses network_mode service:<gluetun>, gluetun has no profile gate,
                the client publishes no ports
  reachability  files that also run the server (ROOT, ALL_IN_ONE): gluetun and the server
                share a network, that network's subnet is inside gluetun's
                FIREWALL_OUTBOUND_SUBNETS, and the client URL host:port is the server's
                ipv4_address on it and its VPN_SENTINEL_SERVER_API_PORT (gluetun's DNS cannot
                resolve compose service names). The firewall check is belt and braces: gluetun
                already accepts its own attached subnet, so it catches a narrowed allowlist
                rather than proving reachability on its own.
Both scope sets are pinned by a test, so a file silently dropping out is caught.

Guard rules (CLAUDE.md): every guard has a mutation test proving it red, each mutation
asserts every OTHER guard still passes (assert_only_guard_fails), and each selector is
asserted to match something.

Without docker the tests skip; VPN_SENTINEL_REQUIRE_DOCKER=1 (set in CI) makes that a failure.
"""

import functools
import ipaddress
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest
from test_release_workflow_guards import assert_only_guard_fails

REPO_ROOT = Path(__file__).resolve().parents[2]

ROOT = "compose.yaml"
ALL_IN_ONE = "deployments/all-in-one/compose.yaml"
CLIENT_WITH_VPN = "deployments/client-with-vpn/compose.yaml"
CLIENT_STANDALONE = "deployments/client-standalone/compose.yaml"
SERVER_CENTRAL = "deployments/server-central/compose.yaml"

ALL_FILES = [ROOT, ALL_IN_ONE, CLIENT_WITH_VPN, CLIENT_STANDALONE, SERVER_CENTRAL]
NAMESPACE_SCOPE = {ROOT, ALL_IN_ONE, CLIENT_WITH_VPN}
REACHABILITY_SCOPE = {ROOT, ALL_IN_ONE}

IMAGE_RE = re.compile(r"^agigante80/vpn-sentinel-(server|client):[^:\s]+$")


# ---------------------------------------------------------------------------------
# Resolving
# ---------------------------------------------------------------------------------


def _docker_available():
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "compose", "version"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _require_docker():
    if _docker_available():
        return
    if os.environ.get("VPN_SENTINEL_REQUIRE_DOCKER") == "1":
        pytest.fail("docker compose is required (VPN_SENTINEL_REQUIRE_DOCKER=1) but is not available")
    pytest.skip("docker compose not available")


def env_file_for(rel):
    return REPO_ROOT / Path(rel).parent / ".env.example"


def resolved_compose(path, env_file):
    """Return the resolved compose config of `path` as a dict, as Docker applies it."""
    _require_docker()
    cmd = [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "--profile",
        "*",
        "-f",
        str(path),
        "config",
        "--format",
        "json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, f"docker compose config failed for {path}: {proc.stderr}"
    return json.loads(proc.stdout)


@functools.lru_cache(maxsize=None)
def real(rel):
    return resolved_compose(REPO_ROOT / rel, env_file_for(rel))


def mutate(rel, old, new, tmp_path):
    """Apply one text replacement to a real compose file, write it to tmp_path and return
    its resolved config. Asserts the anchor exists, so a mutation can never test nothing."""
    text = (REPO_ROOT / rel).read_text()
    assert old in text, f"mutation anchor not found in {rel}: {old!r}"
    mutated = text.replace(old, new, 1)
    assert mutated != text, "mutation must change the compose text"
    target = tmp_path / "compose.yaml"
    target.write_text(mutated)
    return resolved_compose(target, env_file_for(rel))


# ---------------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------------


def services_with_image(cfg, needle):
    return {name: svc for name, svc in cfg.get("services", {}).items() if needle in (svc.get("image") or "")}


def sentinel_role(svc):
    """'server' or 'client' for a VPNSentinel service, found by its image or, for a
    build-only service, by the Dockerfile it builds. None for any other service."""
    build = svc.get("build")
    dockerfile = build.get("dockerfile", "") if isinstance(build, dict) else ""
    m = re.search(
        r"vpn-sentinel-(server|client)|vpn_sentinel/(server|client)/Dockerfile", f"{svc.get('image', '')} {dockerfile}"
    )
    return (m.group(1) or m.group(2)) if m else None


def _env(svc):
    env = svc.get("environment") or {}
    return env if isinstance(env, dict) else dict(item.split("=", 1) for item in env)


def _one(cfg, needle, errors, label):
    found = services_with_image(cfg, needle)
    if len(found) != 1:
        errors.append(f"selector for {label} (image containing {needle!r}) matched {len(found)} services, expected 1")
        return None, None
    return next(iter(found.items()))


# ---------------------------------------------------------------------------------
# Guards: take a resolved config, return a list of error strings (empty = pass)
# ---------------------------------------------------------------------------------


def image_errors(cfg):
    """Every VPNSentinel service that names an image must name a published one. A
    build-only service (no image) is built locally and cannot fail to pull."""
    errors = []
    matched = 0
    for name, svc in cfg.get("services", {}).items():
        role = sentinel_role(svc)
        if role is None:
            continue
        matched += 1
        image = svc.get("image")
        if image is not None and not (IMAGE_RE.match(image) and IMAGE_RE.match(image).group(1) == role):
            errors.append(
                f"vpn-sentinel-{role} image {image!r} must be agigante80/vpn-sentinel-{role}:<tag> (service {name})"
            )
    if matched == 0:
        errors.append("image selector matched no vpn-sentinel service")
    return errors


def namespace_errors(cfg):
    errors = []
    vpn_name, vpn = _one(cfg, "gluetun", errors, "gluetun")
    cli_name, cli = _one(cfg, "vpn-sentinel-client", errors, "client")
    if errors:
        return errors
    if cli.get("network_mode") != f"service:{vpn_name}":
        errors.append(f"{cli_name} must use network_mode: service:{vpn_name}")
    if vpn.get("profiles"):
        errors.append(f"{vpn_name} must not define profiles")
    if cli.get("ports"):
        errors.append(f"{cli_name} must not publish ports (publish them on {vpn_name})")
    return errors


def _outbound_subnets(vpn):
    raw = _env(vpn).get("FIREWALL_OUTBOUND_SUBNETS", "")
    return [ipaddress.ip_network(s.strip(), strict=False) for s in raw.split(",") if s.strip()]


def reachability_errors(cfg):
    errors = []
    vpn_name, vpn = _one(cfg, "gluetun", errors, "gluetun")
    cli_name, cli = _one(cfg, "vpn-sentinel-client", errors, "client")
    srv_name, srv = _one(cfg, "vpn-sentinel-server", errors, "server")
    if errors:
        return errors
    shared = sorted(set(vpn.get("networks") or {}) & set(srv.get("networks") or {}))
    if not shared:
        return [f"{vpn_name} and {srv_name} share no network"]
    allowed = _outbound_subnets(vpn)
    url = urlparse(_env(cli).get("VPN_SENTINEL_URL", ""))
    url_host = url.hostname
    url_port = url.port or (443 if url.scheme == "https" else 80)
    srv_port = int(_env(srv).get("VPN_SENTINEL_SERVER_API_PORT") or 5000)
    if url_port != srv_port:
        return [f"client URL port {url_port} is not the {srv_name} VPN_SENTINEL_SERVER_API_PORT {srv_port}"]
    problems = []
    for net in shared:
        subnets = [
            ipaddress.ip_network(c["subnet"])
            for c in ((cfg.get("networks", {}).get(net) or {}).get("ipam") or {}).get("config") or []
            if "subnet" in c
        ]
        srv_ip = (srv["networks"][net] or {}).get("ipv4_address")
        if not subnets:
            problems.append(f"network {net} has no ipam subnet")
        elif not all(any(s.subnet_of(a) for a in allowed) for s in subnets):
            problems.append(
                f"network {net} subnet {[str(s) for s in subnets]} is not inside {vpn_name} "
                f"FIREWALL_OUTBOUND_SUBNETS {[str(a) for a in allowed]}"
            )
        elif not srv_ip:
            problems.append(f"{srv_name} has no ipv4_address on network {net}")
        elif url_host != srv_ip:
            problems.append(f"client URL host {url_host} is not the {srv_name} ipv4_address {srv_ip}")
        else:
            return []  # one fully working shared network is enough
    return problems


GUARDS = {
    "image": lambda cfg: not image_errors(cfg),
    "namespace": lambda cfg: not namespace_errors(cfg),
    "reachability": lambda cfg: not reachability_errors(cfg),
}


def assert_guard(errors_fn, cfg):
    errors = errors_fn(cfg)
    assert not errors, "; ".join(errors)


# ---------------------------------------------------------------------------------
# Real files
# ---------------------------------------------------------------------------------


def _scope(guard_needles):
    return {rel for rel in ALL_FILES if all(services_with_image(real(rel), needle) for needle in guard_needles)}


def test_namespace_scope_is_pinned():
    assert _scope(["gluetun", "vpn-sentinel-client"]) == NAMESPACE_SCOPE


def test_reachability_scope_is_pinned():
    assert _scope(["gluetun", "vpn-sentinel-client", "vpn-sentinel-server"]) == REACHABILITY_SCOPE


@pytest.mark.parametrize("rel", ALL_FILES)
def test_images_are_namespaced(rel):
    assert_guard(image_errors, real(rel))


@pytest.mark.parametrize("rel", sorted(NAMESPACE_SCOPE))
def test_client_runs_in_vpn_namespace(rel):
    assert_guard(namespace_errors, real(rel))


@pytest.mark.parametrize("rel", sorted(REACHABILITY_SCOPE))
def test_client_can_reach_server(rel):
    assert_guard(reachability_errors, real(rel))


def test_root_matches_issue_values():
    cfg = real(ROOT)
    svc = cfg["services"]
    assert svc["vpn-sentinel-client"]["network_mode"] == "service:vpn-client"
    assert svc["vpn-sentinel-server"]["image"].startswith("agigante80/vpn-sentinel-")
    assert svc["vpn-sentinel-server"]["networks"]["vpn-sentinel"]["ipv4_address"] == "198.18.0.10"
    assert _env(svc["vpn-sentinel-client"])["VPN_SENTINEL_URL"].startswith("http://198.18.0.10:5000")
    assert "gluetun:v" in svc["vpn-client"]["image"], "gluetun must be pinned to a release tag"


# ---------------------------------------------------------------------------------
# Mutations: each guard is observed red, and no other guard fires
# ---------------------------------------------------------------------------------

SERVER_NETWORKS_BLOCK = (
    "    networks:\n      vpn-sentinel:\n        ipv4_address: ${VPN_SENTINEL_SERVER_IP:-198.18.0.10}\n"
)
CLIENT_URL = "VPN_SENTINEL_URL=http://${VPN_SENTINEL_SERVER_IP:-198.18.0.10}:${VPN_SENTINEL_SERVER_API_PORT:-5000}"


@pytest.mark.parametrize("rel", sorted(REACHABILITY_SCOPE))
def test_image_guard_negative_unqualified_image(rel, tmp_path):
    cfg = mutate(rel, "image: agigante80/vpn-sentinel-server:latest", "image: vpn-sentinel-server:latest", tmp_path)
    with pytest.raises(
        AssertionError, match="vpn-sentinel-server image 'vpn-sentinel-server:latest' must be agigante80/"
    ):
        assert_guard(image_errors, cfg)
    assert_only_guard_fails(cfg, "image", guards=GUARDS)


@pytest.mark.parametrize("rel", sorted(REACHABILITY_SCOPE))
def test_namespace_guard_negative_missing_network_mode(rel, tmp_path):
    cfg = mutate(rel, "    network_mode: service:vpn-client\n", "", tmp_path)
    with pytest.raises(AssertionError, match="vpn-sentinel-client must use network_mode: service:vpn-client"):
        assert_guard(namespace_errors, cfg)
    assert_only_guard_fails(cfg, "namespace", guards=GUARDS)


@pytest.mark.parametrize("rel", sorted(REACHABILITY_SCOPE))
def test_namespace_guard_negative_profile_gate_readded(rel, tmp_path):
    cfg = mutate(rel, "  vpn-client:\n", '  vpn-client:\n    profiles: ["vpn"]\n', tmp_path)
    with pytest.raises(AssertionError, match="vpn-client must not define profiles"):
        assert_guard(namespace_errors, cfg)
    assert_only_guard_fails(cfg, "namespace", guards=GUARDS)


@pytest.mark.parametrize("rel", sorted(REACHABILITY_SCOPE))
def test_namespace_guard_negative_client_publishes_ports(rel, tmp_path):
    cfg = mutate(
        rel,
        "    network_mode: service:vpn-client\n",
        '    network_mode: service:vpn-client\n    ports:\n      - "18099:8082"\n',
        tmp_path,
    )
    with pytest.raises(AssertionError, match="vpn-sentinel-client must not publish ports"):
        assert_guard(namespace_errors, cfg)
    assert_only_guard_fails(cfg, "namespace", guards=GUARDS)


@pytest.mark.parametrize("rel", sorted(REACHABILITY_SCOPE))
def test_reachability_guard_negative_server_off_shared_network(rel, tmp_path):
    cfg = mutate(rel, SERVER_NETWORKS_BLOCK, "", tmp_path)
    with pytest.raises(AssertionError, match="vpn-client and vpn-sentinel-server share no network"):
        assert_guard(reachability_errors, cfg)
    assert_only_guard_fails(cfg, "reachability", guards=GUARDS)


@pytest.mark.parametrize("rel", sorted(REACHABILITY_SCOPE))
def test_reachability_guard_negative_client_url_host_only(rel, tmp_path):
    cfg = mutate(rel, CLIENT_URL, "VPN_SENTINEL_URL=http://198.18.0.99:5000", tmp_path)
    with pytest.raises(
        AssertionError, match="client URL host 198.18.0.99 is not the vpn-sentinel-server ipv4_address 198.18.0.10"
    ):
        assert_guard(reachability_errors, cfg)
    assert_only_guard_fails(cfg, "reachability", guards=GUARDS)


@pytest.mark.parametrize("rel", sorted(REACHABILITY_SCOPE))
def test_reachability_guard_negative_client_url_port_only(rel, tmp_path):
    cfg = mutate(rel, CLIENT_URL, "VPN_SENTINEL_URL=http://${VPN_SENTINEL_SERVER_IP:-198.18.0.10}:5001", tmp_path)
    with pytest.raises(
        AssertionError, match="client URL port 5001 is not the vpn-sentinel-server VPN_SENTINEL_SERVER_API_PORT 5000"
    ):
        assert_guard(reachability_errors, cfg)
    assert_only_guard_fails(cfg, "reachability", guards=GUARDS)


@pytest.mark.parametrize("rel", sorted(REACHABILITY_SCOPE))
def test_overrides_move_together(rel, tmp_path):
    """Overriding the subnet, server IP and API port in .env keeps every guard green, and the
    resolved server IP sits inside the resolved subnet (the documented override path)."""
    env = tmp_path / ".env"
    env.write_text(
        env_file_for(rel).read_text()
        + "\nVPN_SENTINEL_DOCKER_SUBNET=198.19.0.0/24\nVPN_SENTINEL_SERVER_IP=198.19.0.10\n"
        + "VPN_SENTINEL_SERVER_API_PORT=5001\n"
    )
    cfg = resolved_compose(REPO_ROOT / rel, env)
    for name, ok in GUARDS.items():
        assert ok(cfg), f"guard {name} fails on the override path"
    srv = cfg["services"]["vpn-sentinel-server"]
    net = next(iter(srv["networks"]))
    subnet = ipaddress.ip_network(cfg["networks"][net]["ipam"]["config"][0]["subnet"])
    assert ipaddress.ip_address(srv["networks"][net]["ipv4_address"]) in subnet
    assert _env(cfg["services"]["vpn-sentinel-client"])["VPN_SENTINEL_URL"] == "http://198.19.0.10:5001"


@pytest.mark.parametrize("rel", sorted(REACHABILITY_SCOPE))
def test_reachability_guard_negative_firewall_does_not_cover_subnet(rel, tmp_path):
    cfg = mutate(
        rel,
        "FIREWALL_OUTBOUND_SUBNETS=${VPN_SENTINEL_DOCKER_SUBNET:-198.18.0.0/24}",
        "FIREWALL_OUTBOUND_SUBNETS=198.19.0.0/24",
        tmp_path,
    )
    with pytest.raises(AssertionError, match="is not inside vpn-client FIREWALL_OUTBOUND_SUBNETS"):
        assert_guard(reachability_errors, cfg)
    assert_only_guard_fails(cfg, "reachability", guards=GUARDS)


def test_guards_fail_on_vacuous_selectors():
    empty = {"services": {"web": {"image": "nginx"}}}
    assert image_errors(empty)
    assert namespace_errors(empty)
    assert reachability_errors(empty)
