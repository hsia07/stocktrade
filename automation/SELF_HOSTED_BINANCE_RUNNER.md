# Binance USD-M Prefilter — Self-hosted Runner Setup

GitHub-hosted runners in U.S. Azure regions receive Binance HTTP 451, so the Binance prefilter workflow is intentionally pinned to a self-hosted Linux runner with the custom label `binance`.

## One-time setup

1. Use a Linux machine in a location where Binance USD-M public market data is legally available and reachable.
2. In GitHub open `hsia07/stocktrade` → Settings → Actions → Runners → New self-hosted runner.
3. Choose Linux and the correct CPU architecture. GitHub will show repository-specific download/configuration commands and a short-lived registration token. Run exactly those commands on the target machine.
4. During runner configuration, add the custom label `binance` when prompted, or add that label from the runner settings page after registration.
5. Install the runner as a service using the service commands shown by GitHub so it survives logout/reboot.
6. Verify connectivity on that machine:

```bash
python3 - <<'PY'
import urllib.request
with urllib.request.urlopen('https://fapi.binance.com/fapi/v1/ping', timeout=10) as r:
    print(r.status, r.read().decode())
PY
```

Expected result: HTTP 200 and `{}`.

## Workflow routing

The workflow uses:

```yaml
runs-on: [self-hosted, linux, binance]
```

The job will run only on a registered runner that has all three labels.

## Validation

Once the runner is online, trigger `Binance USD-M Prefilter` manually from GitHub Actions. A valid run must print `BINANCE_PREFLIGHT=PASS`, then a single `SNAPSHOT_JSON=...` payload whose `complete` field is `true`.

Do not re-enable the downstream ChatGPT v4 scanner until at least one full-market prefilter run passes.
