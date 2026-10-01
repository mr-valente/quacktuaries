# Athenaeum deployment contract

Service: `quacktuaries`. Public path: `/quacktuaries/`. Internal port: `8000`. One application process and one SQLite database. Hosted deployments may sleep when idle; shared-account synchronization runs while awake. Timer polling checks game time when a request arrives.

## Runtime

Use `python -m app` for the container entry point. It supplies `ROOT_PATH` to Uvicorn as well as FastAPI, so mounted static files receive the correct ASGI path. Templates and redirects use named routing helpers; timer URLs are JSON-encoded generated URLs. Caddy strips `/quacktuaries` upstream. Empty `ROOT_PATH` supports standalone deployment. Legacy `BASE_URL` and `DATABASE_URL` configuration were unused; `DB_PATH` is authoritative.

Production configuration:

```text
APP_ENV=production
ROOT_PATH=/quacktuaries
PORT=8000
DB_PATH=/data/app.db
SESSION_SECRET_FILE=/run/secrets/quacktuaries_session
FORWARDED_ALLOW_IPS=*
```

Use a protected secret file containing a random key of at least 32 characters. Alternatively set `SESSION_SECRET`, but never both. Missing/short production keys fail startup. The image has no embedded development key. Preserve the secret across replacement: changing it invalidates existing sessions and name-based rejoin ownership.

The cookie is `quacktuaries_session`, scoped to the configured prefix (or `/` standalone), host-only, HttpOnly, SameSite=Lax, and Secure in production. The application does not accept sibling `session` cookies. Athenaeum trusts proxy headers on its private apps network, whose services are trusted peers. That wildcard is supplied by Athenaeum's Compose file, not embedded in the image; standalone deployments should allow only their own trusted proxies. Do not publish application ports in production.

The image runs as UID/GID `10001:10001`, supports a read-only root filesystem, and writes only to `/data` and temporary scratch space. `PORT` is honored by the entry point; the image healthcheck targets the ecosystem's fixed port 8000. Override that check if changing the container port. No root privileges, Docker socket, or cloud credentials are needed.

## Data and health

Mount `/srv/athenaeum/apps/quacktuaries/data/` at `/data`, owned by the runtime UID/GID. Production startup refuses to create a missing parent directory. An explicitly prepared empty directory initializes the existing schema. Shared accounts add the link and outbox tables described below; existing classroom columns are unchanged.

`GET /_health` returns 200 with `{"status":"ok"}` only if a read-only SQLite connection can read the required tables; otherwise 503 with a generic status. It does not create a database or advance gameplay. Caddy keeps this app probe internal. Compose's missing-bind-directory check is not a filesystem UUID/mount check; Athenaeum now supplies the host guard, which must be installed and verified on Oracle before deployment.

The database owns teachers, sessions, players, device statistics, and events. There are no uploads. Consistent full backups must use SQLite's supported backup API and preserve the signing key in encrypted recovery material. Do not copy the live database file periodically; CSV game exports do not restore ownership or complete game state. Athenaeum provides encrypted snapshots and isolated restore tests; see its `docs/guides/5-backup-and-recovery.md`.

The existing Cloud Run deployment is untouched. Changing its image could discard ephemeral data; do not deploy this integration there as a migration shortcut. The cookie name changes from the old generic `session` cookie. Preserve data and plan existing-browser ownership/rejoin behavior during the separate cutover phase.

## Builds and verification

`requirements.txt` records allowed dependency ranges; `requirements.lock` pins the resolved runtime set, including transitives. Docker installs the lock with binary wheels only. The Python base is pinned to a multi-platform digest. The resolved FastAPI/Starlette versions use request-first template rendering, so template calls now use explicit keyword arguments.

After a deliberate dependency update, resolve the entire lock on Python 3.12, review it, verify AMD64 and ARM64 wheels, and run deployment/workflow checks. No downloaded architecture-specific executable is hardcoded into the application. Availability of ARM wheels is not native ARM execution evidence.

```bash
docker build -t quacktuaries:local .
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  -v "$PWD/tests:/tests:ro" quacktuaries:local \
  python -m unittest discover -s /tests -v
```

The tests launch real Uvicorn against disposable databases. Athenaeum's separate browser suite exercises HTTPS prefix routing, teacher/student gameplay, static assets, timer polling, exports, cookies, and replacement persistence through Caddy.

Shared-style version: not adopted yet. The existing appearance remains during Phase C; Athenaeum's `style.md` defines the eventual shared design. The existing guide still loads pinned KaTeX CDN resources. Shared styling and asset packaging are a later phase.

## Manual image delivery

The shared Fish `~/.config/builder/builds.yaml` owns an independent `quacktuaries` entry and SemVer counter. From your normal local Fish shell:

```fish
build --dry-run --version v0.1.0 quacktuaries
build --version v0.1.0 quacktuaries
# Later releases increment only Quacktuaries' version:
build quacktuaries
```

Like Tailgate, one command builds and publishes both output lines at one version:

| Variant | Moving tag | Retained version example | Defaults |
| --- | --- | --- | --- |
| Standalone | `valentemath/quacktuaries:latest` | `valentemath/quacktuaries:v0.1.0` | Root path, development mode |
| Athenaeum | `valentemath/quacktuaries:latest-athenaeum` | `valentemath/quacktuaries:v0.1.0-athenaeum` | `/quacktuaries`, production mode |

The hosted variant requires a session secret at runtime. Standalone production deployments must also set `APP_ENV=production` and supply a persistent secret. Neither recipe depends on an Athenaeum checkout. A plain `docker build .` still selects the standalone target; `docker-compose.yml` remains for local development.

Release `docker/compose.yaml` builds ARM64 for Oracle; set `QUACKTUARIES_PLATFORM=linux/amd64` only when publishing for an AMD64 host. These are single-architecture tags. On AMD64, ARM builds need registered QEMU/binfmt emulation. Add `--no-push --version v0.1.0` for a local build check without publication or version-state changes.

Athenaeum pulls `valentemath/quacktuaries:latest-athenaeum` and updates manually over SSH. Its `ops/runbook/stack update` takes a verified encrypted backup before replacing containers. Schedule updates outside active classes; there is no automatic updater or class-activity gate. Pin a retained image only when compatible with the current database. See Athenaeum's `docs/development/image-builds.md` and `docs/guides/3-daily-usage.md` for publication and deployment.

The app's optional private `python -m app.operations status|drain|release` CLI remains available, but the manual runbook does not call it. Existing Cloud Run deployment triggers must be disabled separately before a source push intended solely for Oracle; preserve live records before the eventual cutover.

## Shared Athenaeum accounts

The hosted stack supplies `ACCOUNT_SERVICE_URL=http://accounts:8000` and
`ATHENAEUM_APP_ID=quacktuaries`. The adapter derives its private API credential from
the existing per-app session key; never expose that credential to the browser.
A standalone image omits these settings and keeps the name-and-join-code flow.

On startup, SQLAlchemy creates the additive `ecosystem_links` and
`ecosystem_outbox` tables. Existing teachers, players, games and tokens are
preserved. Back up the database before deploying. Older images ignore these
tables; retained results and pending deliveries stay on disk when rolling back.

Google-linked players and teachers recover their seats from the shared account
on another browser. Original guest records need an explicit save from a browser
with their rejoin token. Classroom display names do not establish ownership.
Shared sign-out is available through the account overview. Existing unlinked
guest seats remain browser-based.

The outbox is written in the classroom transaction. A background worker retries
every 15 seconds while awake and reconciles finalized records on startup. Sleep
retains pending rows until the next wake. The app account page reports pending
records. An outage retains access only to an established seat with the same
shared cookie and a signed browser binding; fresh or switched identities need
service validation. Google sign-out during an outage is enforced when identity
validation resumes.

The pinned adapter lives in `app/ecosystem.py`; its source and integration
contract are in the Athenaeum repository under `accounts/client/` and
`docs/reference/accounts.md`. Update the copies together.
