# Landmines (deploy-watch failure classes)

Known failure classes, checked BEFORE a deploy so the prediction comes before the explosion, and
used to tell a real failure from a normal deploy while it runs. These are classes seen on Umbraco
Cloud that are not specific to one site; your project's own go in `references/project.md`.

Examples use a made-up site, **Acme Events**, with invented timestamps, ids and process numbers.

## 1. A normal Cloud deploy looks alarming — do NOT escalate on these

- **Minutes of 503.** While the app restarts, public pages return 503, and Cloud serves its own
  maintenance page ("Site Temporarily Unavailable", `noindex, nofollow`) rather than an Umbraco
  error page. A few minutes is normal; to tell a restart from an outage, check another environment
  as a control.
- **Two boots.** The app can start, stop and start again within a minute or so: extract, then
  restart. The process id changes twice.
- **Shutdown noise from the old instance** as it drains, such as
  `Cannot access a disposed object. Object name: 'IServiceProvider'`. It comes from the process
  that is going away.
- **`Skipping Umbraco content and/or schema import at startup, because no files are provided`** is
  an unrelated startup path doing nothing. It is **not** Deploy's schema pass.
- **Readiness probes failing while migrations run.** Each probe logs the `umbraco-ready` health
  check as `Unhealthy` with `Level: Upgrading`, many times, between `restarting` and `serving`.
- **A progress-polling timeout just before the schema pass.** An `Error` with
  `System.TimeoutException` from `WorkEnvironment.GetProgressAsync` on
  `/umbraco/umbracodeploy/statusreport/get/<workId>`. The portal asks for progress before the work
  item exists to answer. The same `<workId>` then appears in `Beginning deployment "<workId>"`, and
  the deploy proceeds normally.

*Example:* how a normal deploy reads in the watch output (abridged):

```json
{"timestamp":"2026-03-12T09:06:10Z","phase":"restarting","type":"phase"}
{"timestamp":"2026-03-12T09:06:12Z","type":"log-monitor","status":"unavailable"}
{"timestamp":"2026-03-12T09:07:35Z","phase":"app-alive","type":"phase","detail":{"downFor":"1m25s","managementStatus":401}}
{"timestamp":"2026-03-12T09:07:36Z","type":"log-monitor","status":"resumed"}
{"timestamp":"2026-03-12T09:07:41Z","type":"log","category":"migration","level":"Information","message":"Starting 'Umbraco.Forms' migration plan"}
{"timestamp":"2026-03-12T09:09:02Z","phase":"serving","type":"phase"}
```

Escalation threshold: if 503s last much longer than your usual deploy (record yours in
`references/project.md`), stop treating it as a restart and get the portal's deployment log.

## 2. The schema pass runs after the site is serving

`landed` and `serving` are about the *code*: a new process is answering. Deploy applies the schema
in its own pass, which starts AFTER the app is up and is only done at
`Deployment "<id>" completed`. A schema tripwire still at its baseline between `serving` and the end
of the pass is expected, not a finding. If it must be reported early, call it "schema pass still
running", never "did not land".

`deploy watch --uda-dir` handles this: it reads the pass start and end from the log and holds
`verified` until the pass has ended.

*Example:*

```json
{"timestamp":"2026-03-12T09:09:30Z","type":"schema-pass","status":"started"}
{"timestamp":"2026-03-12T09:10:05Z","type":"schema-pass","status":"ended","detail":{"workStatus":"Completed"}}
```

## 3. The schema pass is all-or-nothing

One invalid artifact of ANY type can abort the whole schema pass: unrelated document types and
data types in the same deploy then don't apply either. When predicting impact, the blast radius is
"all schema in this deploy", not "the broken artifact". Package artifacts (forms, automations and
similar) deserve extra attention in the landmine scan: if one is drifted, it will be processed, and
a package's own validation can fail where the CMS's wouldn't.

## 4. Deploy can skip artifacts without failing

A pass can end `Completed` while some artifacts are still missing or drifted on the target. That is
why `deploy watch --uda-dir` exits 7 for "verified, but schema artifacts unconfirmed". Treat exit 7
as "check these artifacts", not as a failed deploy.

## 5. Search can be empty after a deploy that "succeeded"

A deployment can trigger a rebuild of every Examine index. Until it finishes, site search returns
nothing, even though pages render and the deploy reported success. `deploy watch` checks index
health before `verified`, and a rebuild during the settle window restarts the window. If you
verify by hand, run `umbraco indexer list` and look for `docs=0` or Rebuilding.

*Example:*

```json
{"timestamp":"2026-03-12T09:10:40Z","type":"log","category":"indexer","level":"Information","message":"Rebuilding index ExternalIndex"}
```

## 6. Docs-only promotions may not restart anything

A commit that only changes files outside the built site (docs, agent instructions) can reach a
Cloud environment without restarting the app or running a Deploy pass. A watch armed for such a
promotion stays at its baseline until it times out. Check the scope first (step 1); don't use a
docs-only promotion as a rehearsal.

## 7. Chronic noise that predates the deploy

Every busy site logs a few errors and warnings constantly, unrelated to any deploy. Baseline the
log stream before arming, and exclude those lines (`--logs-exclude`, recorded in
`references/project.md`), or every watch reports a false red. The CLI already excludes a few
common ones: the Delivery API "not enabled" indexing line, the readiness-probe `Level: Upgrading`
lines, and a known Automate lock-row duplicate-key error.

## 8. Package APIs blocked by basic auth on non-live environments

With Public Access (basic auth) on, the core Management API still works, but package APIs (Deploy,
Forms, Engage, Automate) and public pages redirect to the basic-auth login. Without the
environment's shared secret in the CLI profile, artifacts from those packages report `unknown`, and
health paths can't be checked. `unknown` is never a clearance.

## A log monitor left running

A log poll armed for a deploy and not stopped at `verified` can run for hours, querying production
and notifying people overnight. It will even surface real problems, and that is exactly why the
rule in SKILL.md is absolute: a deploy watch ends at `verified`, and production monitoring is its
own decision. With `--logs` the log stream stops with the watch; a standalone `logs tail` armed
after a failure must be stopped by hand.
