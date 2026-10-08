# Project: Acme Events (example)

> **This is a made-up example.** Copy it to `references/project.md` and replace everything with
> your own site. The skill reads this file for anything specific to your project; keep the other
> reference files generic.

## Environments

| Env | URL | Umbraco CLI profile | Notes |
|---|---|---|---|
| dev | https://dev.acme-events.example | `acme-dev` | Public Access (basic auth) on: profile has `basicAuthSharedSecret` |
| live | https://www.acme-events.example | `acme-live` | — |

Usually watched: **live**. Dev receives every merge to `main` automatically.

## Key pages

`/` is always watched. These are added when a deploy is riskier (package upgrades, migrations,
shared layout, navigation or search): `/events/` (listing, content queries), `/search/?q=jazz`
(uses the search index). Pick pages that render real content, not a static file, so a broken
content cache shows up.

## Schema folder

`src/AcmeEvents.Web/umbraco/Deploy/Revision`

Export it from the branch being deployed before steps 3 and 4:

```bash
git archive origin/main src/AcmeEvents.Web/umbraco/Deploy/Revision | tar -x -C /tmp/acme-schema
```

## Bookmark

Tag prefix `deploy/live/`, e.g. `deploy/live/2026-03-12-0915`. `scripts/deploy-scope.py` treats
these paths as repo-only (no site effect): `.github/`, `.claude/`, `docs/`, `tests/`, `*.md`.

## Health check groups to run after landing

`Live Environment`, `Data Integrity`, `Forms` (`umbraco health groups --profile acme-live` lists them).

## Extra log exclusions

None yet. Add `--logs-exclude "<text>"` here for chronic lines your site logs all the time, with
the date you first saw them, so a deploy is never blamed for them.

## Project landmines

Failure classes seen on this site only. Generic ones go in `landmines.md`.

### Example: event importer errors for a minute after every deploy

The scheduled importer starts before the content cache is warm and logs
`EventImportJob: content root not found` once or twice within 60 s of `serving`. It recovers on
its next run. Expected; don't escalate unless it repeats after `verified`.

## Field notes

Dated lessons from real watches on this project, newest first. Example:

- **2026-03-12, live:** the `/events/` page took 40 s longer than `/` to return 200 after
  `serving`. It renders a large listing on first request; not a failure.
