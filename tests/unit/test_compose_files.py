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

Two more guards were added by #132. They read the RAW YAML text, not the resolved config,
because Compose resolves away exactly what they check (it substitutes variables, and it
drops top-level networks no service joins, so a guard on the resolved config could never fire):
  env           every file: each bare ${VAR} (also ${VAR:?msg}) in an uncommented line has an
                uncommented VAR= line in the .env.example of the same directory. ${VAR:-x},
                ${VAR-x}, ${VAR:+x} and ${VAR+x} are exempt (they carry their own value).
  network       every file with a top-level `networks:` key: each declared network is joined by
                at least one service (list or mapping form)
Subjects: every guard takes a `Compose`, a dict (the resolved config, as before) that also
carries .rel, .text (the raw compose YAML) and .env_text (the matching .env.example). That
keeps ONE registry, so assert_only_guard_fails cross-checks all five guards on each mutation.

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
import yaml
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
NETWORK_SCOPE = {ROOT, ALL_IN_ONE}  # files with a top-level `networks:` key

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


class Compose(dict):
    """The resolved config (a dict, so the #129 guards are unchanged) plus the raw inputs
    the #132 guards read: .rel (display name), .text (compose YAML), .env_text (.env.example)."""

    def __init__(self, cfg, rel, text, env_text):
        super().__init__(cfg)
        self.rel = rel
        self.text = text
        self.env_text = env_text


@functools.lru_cache(maxsize=None)
def real(rel):
    return Compose(
        resolved_compose(REPO_ROOT / rel, env_file_for(rel)),
        rel,
        (REPO_ROOT / rel).read_text(),
        env_file_for(rel).read_text(),
    )


def build(rel, text, tmp_path, env_text=None):
    """Write `text` (and `env_text`, else the real .env.example is used) under tmp_path,
    resolve it, and return the Compose subject."""
    target = tmp_path / "compose.yaml"
    target.write_text(text)
    env_file = env_file_for(rel)
    if env_text is None:
        env_text = env_file.read_text()
    else:
        env_file = tmp_path / ".env.example"
        env_file.write_text(env_text)
    return Compose(resolved_compose(target, env_file), rel, text, env_text)


def mutate(rel, old, new, tmp_path, env_text=None):
    """Apply one text replacement to a real compose file and return the resolved subject.
    Asserts the anchor exists, so a mutation can never test nothing."""
    text = (REPO_ROOT / rel).read_text()
    assert old in text, f"mutation anchor not found in {rel}: {old!r}"
    mutated = text.replace(old, new, 1)
    assert mutated != text, "mutation must change the compose text"
    return build(rel, mutated, tmp_path, env_text)


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


VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:?[-+?=][^}]*)?\}")


def _live_lines(text):
    """Lines with comments removed: whole-line comments and ` # ...` trailers."""
    for line in text.splitlines():
        if not line.lstrip().startswith("#"):
            yield re.sub(r"\s#.*$", "", line)


def required_vars(text):
    """Variables a compose file needs defined: a bare ${VAR} or ${VAR:?msg} / ${VAR?msg}.
    ${VAR:-x}, ${VAR-x}, ${VAR:+x}, ${VAR+x} carry their own value and are exempt."""
    found = set()
    for line in _live_lines(text):
        for name, op in VAR_RE.findall(line):
            if not op or op.lstrip(":").startswith("?"):
                found.add(name)
    return found


def defined_vars(env_text):
    """Variables with an uncommented KEY= line (optionally `export KEY=`)."""
    return {m.group(1) for line in env_text.splitlines() if (m := re.match(r"\s*(?:export\s+)?([A-Za-z_]\w*)=", line))}


def env_errors(subject):
    needed = required_vars(subject.text)
    if not needed:
        return [f"{subject.rel} references no required ${{VAR}}: env selector matched nothing"]
    defined = defined_vars(subject.env_text)
    return [f"{subject.rel} references ${{{v}}} not defined in .env.example" for v in sorted(needed - defined)]


def network_errors(subject):
    doc = yaml.safe_load(subject.text) or {}
    declared = doc.get("networks") or {}
    joined = set()
    for svc in (doc.get("services") or {}).values():
        nets = (svc or {}).get("networks") or []
        joined.update(nets)  # list form: names; mapping form: keys
    return [f"{subject.rel} declares network '{n}' that no service joins" for n in sorted(declared) if n not in joined]


GUARDS = {
    "image": lambda cfg: not image_errors(cfg),
    "namespace": lambda cfg: not namespace_errors(cfg),
    "reachability": lambda cfg: not reachability_errors(cfg),
    "env": lambda cfg: not env_errors(cfg),
    "network": lambda cfg: not network_errors(cfg),
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
    cfg = Compose(resolved_compose(REPO_ROOT / rel, env), rel, (REPO_ROOT / rel).read_text(), env.read_text())
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
    assert env_errors(Compose(empty, "x.yaml", "services:\n  web:\n    image: nginx\n", ""))


# ---------------------------------------------------------------------------------
# #132: env and network guards (raw YAML)
#
# Why the mutation tests here still prove "only its own guard fires": the #129 guards read
# the resolved config, the #132 guards read raw text, and assert_only_guard_fails takes ONE
# subject. Each mutation therefore builds a Compose from the MUTATED raw text AND resolves
# that same text with docker, so all five guards judge the same mutated file and the
# registry cross-check is unchanged. Mutations are chosen to be invisible to the other
# guards (an x- extension field, an extra network no service joins), and the cross-check
# asserts that.
# ---------------------------------------------------------------------------------

EXTENSION_ANCHOR = "services:\n"


def with_probe(rel, tmp_path, reference, env_text=None):
    """Mutate rel by adding a top-level x- extension field holding `reference`, which Compose
    accepts and no other guard looks at."""
    return mutate(rel, EXTENSION_ANCHOR, f"x-probe: {reference}\nservices:\n", tmp_path, env_text)


def test_compose_file_set_is_pinned():
    shipped = {
        str(p.relative_to(REPO_ROOT))
        for p in [REPO_ROOT / "compose.yaml", *REPO_ROOT.glob("deployments/*/compose.yaml")]
    }
    assert shipped == set(ALL_FILES)
    assert len(ALL_FILES) == 5


def test_env_selector_is_not_vacuous():
    for rel in ALL_FILES:
        assert required_vars(real(rel).text), f"{rel} references no required variable: env guard would pass vacuously"


def test_network_scope_is_pinned():
    declared = {rel for rel in ALL_FILES if (yaml.safe_load(real(rel).text) or {}).get("networks")}
    assert declared == NETWORK_SCOPE and declared, "network guard needs at least one in-scope file"


@pytest.mark.parametrize("rel", ALL_FILES)
def test_every_required_variable_is_in_its_own_env_example(rel):
    assert_guard(env_errors, real(rel))


@pytest.mark.parametrize("rel", ALL_FILES)
def test_every_declared_network_is_joined(rel):
    assert_guard(network_errors, real(rel))


def test_required_var_forms():
    text = "a: ${A}\nb: ${B:-x}\nc: ${C-x}\nd: ${D:?need}\ne: ${E:+x}\nf: ${F+x}\n"
    assert required_vars(text) == {"A", "D"}


def test_env_guard_negative_undefined_variable(tmp_path):
    subject = with_probe(ROOT, tmp_path, "${VPN_SENTINEL_DOES_NOT_EXIST}")
    with pytest.raises(
        AssertionError, match=r"compose.yaml references \$\{VPN_SENTINEL_DOES_NOT_EXIST\} not defined in .env.example"
    ):
        assert_guard(env_errors, subject)
    assert_only_guard_fails(subject, "env", guards=GUARDS)


@pytest.mark.parametrize("rel", ALL_FILES)
def test_env_guard_negative_every_file(rel, tmp_path):
    subject = with_probe(rel, tmp_path, "${VPN_SENTINEL_DOES_NOT_EXIST}")
    assert env_errors(subject) == [f"{rel} references ${{VPN_SENTINEL_DOES_NOT_EXIST}} not defined in .env.example"]
    if rel in REACHABILITY_SCOPE:
        assert_only_guard_fails(subject, "env", guards=GUARDS)
    else:
        # The namespace and reachability guards are scoped (their selectors correctly find no
        # gluetun/server here and report so), so the all-guards cross-check applies only to the
        # files in their scope. Outside it, check the guards that apply to every file.
        assert image_errors(subject) == [] and network_errors(subject) == []


def test_env_guard_positive_default_is_exempt(tmp_path):
    subject = with_probe(ROOT, tmp_path, "${VPN_SENTINEL_NOT_IN_ENV:-fallback}")
    assert "VPN_SENTINEL_NOT_IN_ENV" not in subject.env_text
    assert_guard(env_errors, subject)
    assert all(ok(subject) for ok in GUARDS.values())


def test_env_guard_negative_commented_definition_does_not_count(tmp_path):
    """A `# VAR=x` line in .env.example is not a definition (this is how #130 left the TLS paths)."""
    env_text = real(ROOT).env_text + "\n# VPN_SENTINEL_ONLY_COMMENTED=x\n"
    subject = with_probe(ROOT, tmp_path, "${VPN_SENTINEL_ONLY_COMMENTED}", env_text)
    with pytest.raises(
        AssertionError, match=r"compose.yaml references \$\{VPN_SENTINEL_ONLY_COMMENTED\} not defined in .env.example"
    ):
        assert_guard(env_errors, subject)
    assert_only_guard_fails(subject, "env", guards=GUARDS)


def test_env_guard_positive_uncommented_definition_counts(tmp_path):
    env_text = real(ROOT).env_text + "\nVPN_SENTINEL_NOW_DEFINED=x\n"
    subject = with_probe(ROOT, tmp_path, "${VPN_SENTINEL_NOW_DEFINED}", env_text)
    assert_guard(env_errors, subject)


def test_env_guard_positive_commented_compose_line_is_ignored(tmp_path):
    subject = mutate(
        ROOT, EXTENSION_ANCHOR, "# ${VPN_SENTINEL_IN_A_COMMENT}\nservices:\n", tmp_path
    )  # whole-line comment
    assert_guard(env_errors, subject)


@pytest.mark.parametrize("rel", sorted(NETWORK_SCOPE))
def test_network_guard_negative_orphan_network(rel, tmp_path):
    subject = mutate(rel, "\nnetworks:\n", "\nnetworks:\n  vpn-sentinel-orphan:\n    driver: bridge\n", tmp_path)
    assert network_errors(subject) == [f"{rel} declares network 'vpn-sentinel-orphan' that no service joins"]
    with pytest.raises(AssertionError, match="declares network 'vpn-sentinel-orphan' that no service joins"):
        assert_guard(network_errors, subject)
    assert "vpn-sentinel-orphan" not in subject.get(
        "networks", {}
    ), "compose drops orphans: resolved config cannot see it"
    assert_only_guard_fails(subject, "network", guards=GUARDS)


def test_network_guard_accepts_list_and_mapping_forms():
    joined_list = Compose({}, "x.yaml", "services:\n  a:\n    networks: [n]\nnetworks:\n  n: {}\n", "")
    joined_map = Compose({}, "x.yaml", "services:\n  a:\n    networks:\n      n: {}\nnetworks:\n  n: {}\n", "")
    assert not network_errors(joined_list)
    assert not network_errors(joined_map)


# ---------------------------------------------------------------------------------
# Dashboard toggle name (not a registered guard)
# ---------------------------------------------------------------------------------

DASHBOARD_TOGGLE = "VPN_SENTINEL_SERVER_WEB_DASHBOARD_ENABLED"


def test_server_code_reads_the_dashboard_toggle_name():
    """The name pinned above must be the one the server reads, so this test cannot drift."""
    source = (REPO_ROOT / "src/vpn_sentinel/server/__main__.py").read_text()
    assert f'os.getenv("{DASHBOARD_TOGGLE}"' in source


@pytest.mark.parametrize("rel", ALL_FILES)
def test_server_sets_the_dashboard_toggle_the_code_reads(rel):
    servers = {n: s for n, s in real(rel).get("services", {}).items() if sentinel_role(s) == "server"}
    if not servers:
        pytest.skip(f"{rel} does not define the server")
    for name, svc in servers.items():
        env = _env(svc)
        wrong = sorted(k for k in env if "DASHBOARD_ENABLED" in k and k != DASHBOARD_TOGGLE)
        assert not wrong, f"{rel}:{name} sets {wrong}, but the server reads {DASHBOARD_TOGGLE}"
        assert DASHBOARD_TOGGLE in env, f"{rel}:{name} does not set {DASHBOARD_TOGGLE}"
