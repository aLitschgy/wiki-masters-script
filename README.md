# Wiki Masters – automatic pack opening

Python script that opens the available packs on wiki-masters.com, prints the cards obtained
(colored by rarity) and handles authentication by itself.

Docker image: [`alitschgy/wiki-masters-script`](https://hub.docker.com/r/alitschgy/wiki-masters-script)

## How it works

- Opens one pack every `--delay` seconds (10 by default).
- Stops when no packs are left (`packs_remaining == 0`), on a 401, or on any other HTTP error.
- Automatic Supabase authentication, with as few calls as possible:
  1. the saved session is reused as long as its token is valid;
  2. otherwise it is renewed with the `refresh_token` (the new session is written back immediately);
  3. otherwise it falls back to email + password login (see the captcha note below).

Rarities: `C` light green · `PC` light blue · `R` purple · `SR` magenta · `UR` orange · `L` gold · ✨ = shiny.

## Bootstrapping the session (captcha)

Password login is protected by a captcha, so the script cannot use it on its own (`captcha_failed`).
You therefore have to **provide the cookie of a session opened in your browser once**; after that the
script renews the session by itself through the `refresh_token` (no captcha involved).

1. Open a **private browsing window** and log in on wiki-masters.com.
2. DevTools → Network: select a request to the site → copy the value of the `Cookie` header
   (or Storage → Cookies: the values of `sb-…-auth-token.0` and `.1`).
3. Put it in `WIKIMASTERS_COOKIE` (`.env`: `WIKIMASTERS_COOKIE=sb-…-auth-token.0=…; sb-…-auth-token.1=…`).
4. Close the private window **without logging out** (logging out revokes the session) and do not reuse
   that session in the browser: the refresh token rotates on every renewal, so using it from both
   places would invalidate it.

The cookie is only read when no session has been saved yet; you can remove it from `.env` afterwards.
If the session is ever invalidated, repeat the procedure (delete `session.json` / the data folder first).

## Configuration

Environment variables:

| Variable | Required | Description |
|---|---|---|
| `WIKIMASTERS_COOKIE` | yes (first start) | `sb-…-auth-token` cookie of a browser session (see above) |
| `WIKIMASTERS_EMAIL` / `WIKIMASTERS_PASSWORD` | no | Password login, unusable while the captcha is active |
| `WIKIMASTERS_STATE_FILE` | no | Session file (default `./session.json`; `/data/session.json` in Docker) |
| `SUPABASE_ANON_KEY` | no | Public Supabase key (default: the one used by the site) |
| `FORCE_COLOR` | no | `1` keeps colors outside a terminal (e.g. `docker logs`); `NO_COLOR` disables them |

Command-line options:

| Option | Default | Description |
|---|---|---|
| `--delay S` | `10` | Pause between two packs (seconds) |
| `--max N` | `0` | Max packs per pass (0 = unlimited) |
| `--interval S` | `0` | Run again every S seconds (e.g. `3600`); 0 = a single pass |

> `session.json` and `.env` give access to your account: never commit them (already in `.gitignore`).

## Command-line usage

Python 3.10+ required.

```bash
pip install -r requirements.txt

export WIKIMASTERS_COOKIE='sb-…-auth-token.0=…; sb-…-auth-token.1=…'   # first start only

python open_packs.py                       # one pass, until no packs are left
python open_packs.py --max 1               # a single pack (test)
python open_packs.py --delay 5             # 5 s between packs
python open_packs.py --interval 3600       # one pass every hour, continuously
```

For an hourly run through cron instead of `--interval`:

```cron
0 * * * * cd /path/to/wiki-masters-script && python open_packs.py >> packs.log 2>&1
```

## Docker Compose usage

The compose file uses the published image `alitschgy/wiki-masters-script` (it can also be built locally).

1. Create the `.env` file and the data folder (the container runs as uid 1000, which must be able to write to it):
   ```bash
   cp .env.example .env    # then fill in WIKIMASTERS_COOKIE
   mkdir wikimasters-data
   ```
2. Start:
   ```bash
   docker compose up -d
   docker compose logs -f
   ```
   Use `docker compose up -d --build` to build the image locally instead of pulling it.

The container runs one pass per hour (`--interval 3600`, editable in the `command:` of
`docker-compose.yml`) and restarts automatically. The session is stored in `./wikimasters-data/session.json`:
it survives restarts, so the cookie is only used on the first start or if the refresh token is invalidated.

Useful commands:

```bash
docker compose run --rm wikimasters --max 1   # test: one pack, one pass
docker compose pull && docker compose up -d   # update to the latest image
docker compose down                           # stop (the data folder is kept)
```

Without Compose:

```bash
docker run --rm --env-file .env -v "$PWD/wikimasters-data:/data" alitschgy/wiki-masters-script --max 1
```

## Project structure

- `open_packs.py` – entry point, pack-opening loop and CLI options
- `auth.py` – Supabase session (persistence, refresh, login) and cookie building
- `display.py` – colored display of the cards

## Releasing (Docker Hub)

Pushing a git tag starting with `v` triggers `.github/workflows/docker-publish.yml`, which builds a
multi-arch image (`linux/amd64`, `linux/arm64`) and pushes it to Docker Hub as `alitschgy/wiki-masters-script`
with the tags `X.Y.Z`, `X.Y`, `X` and `latest`.

```bash
git tag v1.0.0
git push origin v1.0.0
```

The GitHub environment `Dockerhub` (Settings → Environments) needs the secrets `DOCKERHUB_USERNAME` and
`DOCKERHUB_TOKEN` (a Docker Hub access token with write permission).
