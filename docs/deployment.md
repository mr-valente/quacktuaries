# Athenaeum deployment contract

Service: `quacktuaries`. Public path: `/quacktuaries/`. Internal port: `8000`. One application process and one SQLite database. The app stays awake; there are no independent background jobs. Timer polling checks game time when a request arrives.

## Runtime

Use `python -m app` for the container entry point. It supplies `ROOT_PATH` to Uvicorn as well as FastAPI, so mounted static files receive the correct ASGI path. Templates and redirects use named routing helpers; timer URLs are JSON-encoded generated URLs. Caddy strips `/quacktuaries` upstream. Empty `ROOT_PATH` supports standalone deployment. Legacy `BASE_URL` and `DATABASE_URL` configuration were unused; `DB_PATH` is authoritative.

Production configuration:

```text
APP_ENV=production
ROOT_PATH=/quacktuaries
PORT=8000
DB_PATH=/data/app.db
SESSION_SECRET_FILE=/run/secrets/quacktuaries_session
FORWARDED_ALLOW_IPS=<edge IP on the dedicated Docker network>
```

Use a protected secret file containing a random key of at least 32 characters. Alternatively set `SESSION_SECRET`, but never both. Missing/short production keys fail startup. The image has no embedded development key. Preserve the secret across replacement: changing it invalidates existing sessions and name-based rejoin ownership.

The cookie is `quacktuaries_session`, scoped to the configured prefix (or `/` standalone), host-only, HttpOnly, SameSite=Lax, and Secure in production. The application does not accept sibling `session` cookies. Do not set wildcard proxy trust; Athenaeum supplies Caddy's fixed private IP. Do not publish application ports in production.

The image runs as UID/GID `10001:10001`, supports a read-only root filesystem, and writes only to `/data` and temporary scratch space. `PORT` is honored by the entry point; the image healthcheck targets the ecosystem's fixed port 8000. Override that check if changing the container port. No root privileges, Docker socket, or cloud credentials are needed.

## Data and health

Mount `/srv/athenaeum/apps/quacktuaries/data/` at `/data`, owned by the runtime UID/GID. Production startup refuses to create a missing parent directory. An explicitly prepared empty directory initializes the existing schema. There are no schema changes in this integration.

`GET /_health` returns 200 with `{"status":"ok"}` only if a read-only SQLite connection can read the required tables; otherwise 503 with a generic status. It does not create a database or advance gameplay. Caddy keeps this app probe internal. Compose's missing-bind-directory check is not a filesystem UUID/mount check; Athenaeum now supplies the host guard, which must be installed and verified on Oracle before deployment.

The database owns teachers, sessions, players, device statistics, and events. There are no uploads. Consistent full backups must use SQLite's supported backup API and preserve the signing key in encrypted recovery material. Do not copy the live database file periodically; CSV game exports do not restore ownership or complete game state. Athenaeum's Phase D tools provide encrypted snapshots and isolated restore tests; configuration and host activation are documented in that repository's `docs/recovery.md`.

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

## Phase E delivery

`.github/workflows/images.yml` tests native AMD64/ARM64 images and publishes Docker Hub `:latest` only after both pass. Configure `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, and `ENABLE_PUBLICATION`; see Athenaeum's `docs/delivery.md`. There are no GitHub release assets. `ci/images.json` declares the image name, shared style, and schema version (currently 0). The host checks every 15 minutes and deploys a fixed digest. Schema-changing releases require a maintenance task. The publisher is kept identical in both repositories.

`python -m app.operations status|drain|release` is a private container CLI, with no HTTP route. It exposes only schema, hold, and active-class booleans. Every lobby or non-ended session blocks updates. The request middleware holds a shared lock through each response; drain obtains the exclusive lock before checking activity and placing a transient maintenance hold. Held public requests return 503/Retry-After, while health remains available. This closes the race where a class starts during a download or an in-flight request. The hold lives in container-local `/tmp`, not persistent app data.

The host requires a verified encrypted backup before Quacktuaries replacement and defers for classes; it never restores an old database automatically to make image rollback succeed. Real-server tests cover lobby/active deferral, maintenance responses, and an admitted request completing before the drain decision. Cloud Run and final shared styling remain unchanged by this local work.
