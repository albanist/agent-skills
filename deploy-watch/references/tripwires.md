# Tripwires (deploy-watch method)

A tripwire is a change on the target environment that ONLY the deployment being watched can cause.
Good tripwires are binary, cheap to check, and specific to this deploy.

The examples use a made-up site, **Acme Events**, with made-up ids and values.

## Deriving per artifact class

- **Schema (`.uda` files in the diff)** — the strongest class, and a mechanical one:
  `deploy watch --uda-dir` tracks every drifted or missing artifact and reports each change in its
  own `schema` line. Spot-check by hand only when a line needs explaining:
  `umbraco doctype get <guid> --profile <env>` (or `datatype get`, `template get`). 404 → found is
  unambiguous: only Deploy's schema pass creates that GUID.

  *Example:* the PR adds an `eventPage` document type. At baseline it is missing on live; after the
  pass the watch reports:

  ```json
  {"timestamp":"2026-03-12T09:14:02Z","type":"schema","file":"document-type__4f0c2a9e1b7d4c3a9e5f6a7b8c9d0e1f.uda","kind":"document-type","name":"Event Page","status":"in-sync","previous":"missing-remote"}
  ```

- **Code — views, partials, CSS** — a marker in rendered output: a new class name, a changed
  header, a new element. Prefer markup the change *always* emits over markup that needs editor
  action first.

  *Example:* the PR adds a featured flag to event cards, rendered as `event-card--featured` on
  every card whose event is featured. Check a page that already has a featured event:
  `curl -s https://www.acme-events.example/events/ | grep -c 'event-card--featured'` → `0` before,
  `>0` after.

- **Code — C# behaviour** — a probe request whose response only the new code produces (a changed
  JSON shape, a new endpoint answering 200, a fixed bug's symptom gone). Symptom, not mechanism.

  *Example:* the PR adds `startTime` to `/api/events`:
  `curl -s https://www.acme-events.example/api/events | jq '.[0] | has("startTime")'` → `false`
  before, `true` after.

- **Config (appsettings in the diff)** — usually only observable through behaviour; treat it as code.
- **Content** — not carried by deployments (it lives in the database). No tripwire; verify with CLI
  reads if relevant.

Looping GUIDs through the CLI in zsh: keep the subcommand in separate words
(`umbraco "$kind" get "$guid"`). zsh does not word-split an unquoted `$cmd`, so `cmd="doctype get"`
runs `umbraco 'doctype get'` and every lookup fails as an unknown command, not a 404.

## Baseline rule

Verify each tripwire is ABSENT (404 / marker missing / old value) on the target BEFORE the deploy
starts. A tripwire that is already true is a dead signal — replace it. Record the baselines.

## Compare against what is deployed

`--uda-dir` must point at the schema folder **as it is on the branch being promoted**, not your
working tree. With a feature branch checked out, the comparison includes unreleased schema and
reports drift this deploy will never fix. Export the folder first:

```bash
git archive origin/main <schema folder> | tar -x -C <tmp>
```

## Landing signals — `umbraco deploy watch`

The CLI implements the generic ones: app-restart detection through the newest log entry's
`ProcessId`/`MachineName`, the management API's token endpoint flipping from 503 to a 4xx (the
earliest all-clear, usually before public pages return 200), health-path polling, and index health.
Don't reproduce them by hand. The exact 4xx varies (401 or 400 have both been seen); any 4xx means
the app is answering.

*Example:* the first lines of a live watch:

```json
{"timestamp":"2026-03-12T09:02:41Z","phase":"baseline","type":"phase","detail":{"processId":"5120","healthyPaths":["/","/events/","/contact/"]}}
{"timestamp":"2026-03-12T09:06:10Z","phase":"restarting","type":"phase"}
{"timestamp":"2026-03-12T09:07:35Z","phase":"app-alive","type":"phase","detail":{"downFor":"1m25s","managementStatus":401}}
```

(Abridged: real lines carry more detail.)

What still belongs to you: **artifact tripwires** for code and config. Phases prove the app
recycled; they say nothing about whether *your* change shipped. Derive those from the diff (above)
and check them in step 5.

A watch needs an *in-progress* vocabulary as well as success and failure ones. Otherwise silence is
ambiguous, and the user ends up telling you the deploy landed.

## Health signals (the failure side)

`deploy watch` polls the health paths (`--health-path` is repeatable). Two checks it does not fold
into the phases, both worth running in step 5:

- `umbraco indexer list --profile <env>` — any index at `docs=0` / Rebuilding means site search
  returns nothing to visitors, whatever the deploy reported. A deployment can trigger a full index
  rebuild that leaves search empty for many minutes after the site is serving again.
- `umbraco health run <group> --profile <env>` — Umbraco's configuration and integrity checks.
  `health` is a command group: run the groups a deploy can change (`health groups` lists them).
  The health checks don't test database reachability; a database failure shows up as 503s in the
  watch and as errors in the log stream.

## Converge (the schema fallback)

When a schema pass is blocked but the schema must land NOW: apply it directly through the
environment's CLI profile with **GUID parity**. Take the exact keys from the merged `.uda` files
(entity GUID, property keys, container keys) and create with an explicit id (`datatype create
--json`, full-payload `doctype update --json` where convenience flags can't set keys). Deploy
compares by key, so a database that matches the artifacts is in sync, and later passes skip it.

NEVER use random GUIDs: that creates duplicates and collisions when the real pass runs.

## Environment access

- On Umbraco Cloud, an environment with Public Access (basic auth) on exempts the core Management
  API but not package APIs (Deploy, Forms, Engage, Automate) or public pages. Give the profile the
  environment's basic-auth shared secret (`basicAuthSharedSecret`), or those reads fail and the
  watch cannot see the pages.
- Deployment *status* is not observable without a portal or CI API. Effect-based tripwires are the
  primary signal by design; a CI/CD API, if you have one, is a secondary source.
