# Notifications

VPN Sentinel sends its alerts to Telegram and, optionally, to any number of extra targets through
[Apprise](https://github.com/caronc/apprise) (BSD-2-Clause): ntfy, Gotify, Discord, Slack, Matrix,
Pushover, email and 100+ other services. Telegram setup, bot commands and message examples are in
[TELEGRAM.md](TELEGRAM.md). This page covers the extra targets.

## What is sent

The server sends exactly five alerts, and each one goes to every configured channel:

| Alert | Title |
|---|---|
| Server started | `VPN Keepalive Server Started` |
| No clients connected | `No VPN Clients Connected` |
| Clients went silent | `Client Went Silent` (one client) or `N Clients Went Silent` |
| Client connected | `VPN Connected!` |
| Client IP changed | `VPN IP Changed!` |

VPN bypass and DNS leak status are text inside the connected and IP-changed messages, not separate alerts.
Apprise is send-only: the interactive Telegram bot commands (`/ping`, `/status`, `/help`) stay Telegram-only.
Apprise-only operators (no Telegram credentials) get every alert and the startup notice, and no
"Telegram not configured" warning.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `VPN_SENTINEL_APPRISE_URLS` | empty (disabled) | Apprise target URLs, separated by commas and/or whitespace. `VPN_SENTINEL_APPRISE_URLS_FILE` reads the list from a file instead (Docker/Compose secrets); setting both is a fatal error at startup |

Examples (placeholders, replace with your own):

```bash
# One target
VPN_SENTINEL_APPRISE_URLS=ntfys://my-private-topic-7f3a

# Several, comma or space separated
VPN_SENTINEL_APPRISE_URLS=ntfys://my-private-topic-7f3a,gotify://gotify.example.org/app-token discord://webhook-id/webhook-token

# From a file (one URL per line also works)
VPN_SENTINEL_APPRISE_URLS_FILE=/run/secrets/vpn_sentinel_apprise_urls
```

URL syntax for every service is in the [Apprise catalogue](https://github.com/caronc/apprise/wiki). Common ones:
`ntfys://topic`, `gotify://host/token`, `discord://webhook_id/webhook_token`, `mailtos://user:password@example.org`,
`json://host/path` (a generic webhook).

### Installing Apprise

The server image ships with Apprise (it is installed from the optional `notify` extra). The client image does
not contain it. For a source install use `pip install '.[notify]'`. When the variable is set but Apprise is not
installed, the server logs one `apprise not installed` warning and keeps sending to Telegram.

## Behaviour

- **Plain text.** Alerts are written in HTML for Telegram. Apprise converts them per target. For a target that
  forwards the body as is (such as `json://`), VPN Sentinel appends `format=text` unless the URL sets its own
  `format`, so the receiver gets plain text and not raw `<b>` tags.
- **Never blocks.** Sends run on one background worker with a bounded queue of 50 messages. A slow or dead target
  cannot delay a client keepalive. When the queue is full the message is dropped for Apprise targets and a
  `notify` warning is logged (Telegram is unaffected).
- **Timeouts.** Each target gets a 3 second connect and 3 second read timeout unless the URL sets `cto` or `rto`.
- **Failures are warnings, never errors.** Any result other than success (failure, timeout, partial, no match)
  logs a `notify` warning that names only the scheme, for example `json://***`. One failing target does not
  stop the others or Telegram.
- **Queued alerts do not survive a restart.** The queue is in memory.
- **Long alerts.** The multi-client silence alert is split exactly as for Telegram (at most 5 messages), and each
  chunk is one Apprise message.

## Security

Apprise URLs contain tokens. They are masked in the Unraid template, readable from a `_FILE` secret, and never
written to the log: warnings show only `scheme://***`. See [SECURITY_AND_PRIVACY.md](SECURITY_AND_PRIVACY.md) for
what the alerts contain and where they travel.
