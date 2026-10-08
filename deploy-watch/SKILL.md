---
name: deploy-watch
description: Watch an Umbraco Cloud deployment from start to verified, using the Umbraco CLI. Use when the user says "deploying to live, stand by", "watch the deploy", or before any deployment.
---

# Deploy Watch

**Philosophy: effect-based.** Don't ask the pipeline how it's going — observe the target environment for changes that only this deployment can cause. The environment is the truthful status page. A portal or CI API is an optional *extra* signal source, never the primary one.

The point is not the watch itself. The point is that the agent is up to speed with what is going on, so nobody has to poke it: when a deploy goes wrong, it already knows, because it watched it happen.

## Requirements

- [Umbraco CLI](https://github.com/albanistrefi/umbraco_CLI) **0.4.26 or later**, with one profile per environment (`~/.umbraco/<profile>.config.json`). If an environment has Umbraco Cloud's Public Access (basic auth) on, set `basicAuthSharedSecret` in its profile, or package APIs (Deploy, Forms, Automate) and the public pages are unreachable.
- A git repository whose `main` (or equivalent) is what gets promoted.
- `references/project.md` in this skill's folder, describing your project: copy `references/project.example.md` and fill it in. Everything specific to your site lives there; this file and the other references stay generic.

## Hard rules

- **Baseline before arming.** A tripwire that is already true on the target is not a signal — verify each one ABSENT (or at its pre-deploy value) before the deploy starts. No baseline → no watch.
- **Predict before the deploy, don't just react after.** Run the landmine scan (`references/landmines.md`) and state the risk assessment while the deploy can still be held.
- **Silence must only mean "still deploying".** The watch emits on every terminal state — success AND failure signatures (site health, error pages). A watch that can only report good news is not a watch.
- **Never write to an environment without the user's explicit go.** The failure playbook may *propose* a fix (e.g. a GUID-parity schema apply); executing it needs a go, and against live an explicit, unambiguous go.
- **Verification is symptom-level**: assert what a visitor or editor sees on the environment, not just that artifacts processed.
- **`verified` ends the job — disarm everything, then move the bookmark.** Stop `deploy watch` (its `--logs` stream stops with it), say so, and run `scripts/deploy-scope.py --mark <verified commit>` so the next watch's scope starts here. A watch has no mandate past a clean deploy. A monitor left running will find real problems; that is the argument that erodes this rule, and it does not count. Ongoing production monitoring is a separate decision with its own scope and cadence, never the residue of a deploy watch (`references/landmines.md` § A log monitor left running). A promotion done without a watch leaves the bookmark stale: when the user says "deployed to live" after the fact, place it by hand the same way.
- **`failed` and `timeout` do NOT end the job — they start step 6.** `deploy watch` has exited (5 or 6) because it has nothing further to say, but the incident is live. The `--logs` stream ended with the watch, so **arm a standalone `umbraco logs tail --profile <env> --json --heartbeat 1m` straight away**: the log stream is what the diagnosis runs on. Disarm only when the incident is resolved or the user calls it off. `timeout` means status UNKNOWN — never report it as either success or failure.
- **The agent that armed the watch runs it.** Do not hand the watch to a sub-agent: a failure has to land in the context that diagnoses and acts on it. Handing the *fix* to a sub-agent once the cause is known is fine.

## Procedure

### 1. Scope
The environment's position is an annotated git tag on the commit it runs (the bookmark; the tag prefix is in `references/project.md`). Run `scripts/deploy-scope.py` from the repo root: it lists every PR merged since the bookmark, split into **site changes** and **repo-only changes** (CI, docs, tests, agent files) by the paths each PR touches. Report both groups in exactly this shape, one bullet per PR, `#number: headline`, nothing else on the line (a direct commit has no number: use its short SHA and say it is a direct commit):

```
The following items will be deployed:

- #212: Add the featured flag to event cards
- #215: feat(events): expose start time in /api/events

Repo-only, no site effect:

- #214: ci: cache the npm install
```

Only the site group gets tripwires. **This list is not a stopping point.** Do not end the turn or ask the user to confirm it; continue straight into steps 2 to 4, then say the watch is armed and wait for the user to press deploy. Silence from the user is not a go and not a stop; the watch simply stays armed.

If only repo-only changes are going out, say so: a promotion that changes no built output may not restart the app at all (`references/landmines.md` § Docs-only promotions), so there may be nothing for the watch to see.

**First run, no bookmark yet:** the agent can't tell what the environment runs, so it can't list the scope. Ask the user which commit is live (for example from the Cloud portal). If they don't know, watch without a scope list and, at `verified`, place the first bookmark on the commit that was promoted. From then on the agent moves it itself.

Identify the target environment and its CLI profile from `references/project.md`.

### 2. Derive + baseline tripwires
Per `references/tripwires.md`: one observable delta per artifact class in the diff (schema → tracked by `deploy watch --uda-dir` in step 4, no hand-picked GUIDs; code → a marker in rendered output; config → a behaviour probe). Verify each absent on the target NOW and record the baseline.

### 3. Landmine scan — `umbraco deploy status`
Drift is what decides whether a landmine fires: in-sync artifacts are SKIPPED by Deploy's schema pass; drifted ones are PROCESSED, and processing is when the bug bites. The CLI does that comparison across every artifact, so don't hand-roll it. Compare against the schema folder **as it is on the branch being deployed**, not your working tree (`references/tripwires.md` § Compare against what is deployed):

```bash
umbraco deploy status --profile <env> --uda-dir <exported schema folder> -o json
```

Read `summary` (in-sync / drifted / missingRemote / unknown / errors) and the per-artifact rows. Exit 7 = drift found (a documented constant, not a count); `--exit-zero` suppresses it. Artifacts whose API is unreachable report `unknown` — never a false in-sync, but never a clearance either.

Then apply the judgement the CLI cannot: cross-reference the drifted rows against the failure classes in `references/landmines.md` and `references/project.md`, and report the prediction BEFORE the deploy — expected clean, or a named risk with a prepared fallback.

### 4. Arm — `umbraco deploy watch`
The CLI owns the phase machine. Run it in the background and relay its transitions; do not reimplement the polling loop.

```bash
umbraco deploy watch --profile <env> --json --heartbeat 1m --logs \
  --uda-dir <exported schema folder> \
  --health-path / [--health-path <page> ...]
```

Emits NDJSON, one `type` per line. Phases: `baseline → restarting → app-alive → serving → landed → settling → verified | failed | timeout`. Exit 0 verified, 5 failed, 6 unknown, 7 verified but schema artifacts still drifted or missing after Deploy's schema pass (Deploy can skip artifacts without failing the pass). It baselines everything before arming, checks Examine index health, and requires the environment to stay healthy for a full `--settle` window (default 90 s) before `verified`, because a single passing sample is not verification.

**`--logs` puts the log stream in the same output.** The phases answer "did it land and is it healthy"; the diagnosis comes from the logs, and you cannot investigate afterwards what you never watched. `log` lines cover restarts, migrations, indexer suspend/resume/rebuild, Deploy entries and errors; `log-monitor` lines report the log viewer being unavailable during the restart, gaps, and the final count. Known chronic noise is excluded by the CLI; add your own with `--logs-exclude` (list it in `references/project.md`). Log lines never change phases or the exit code, and the stream stops with the watch.

**Health paths: `/` always.** Add more per deploy with `--health-path` when it earns it: every page a tripwire points at (so the pages this deploy changes are watched throughout, not checked once), and a few key pages (listed in `references/project.md`) when the deploy carries package upgrades or migrations, or touches shared layout, navigation or search. Say which pages and why when arming.

**`--uda-dir` checks the schema tripwires.** It tracks the artifacts that are drifted or missing at baseline and holds `verified` until each is in sync, or until Deploy's schema pass has ended and been re-checked. A schema artifact still at baseline before the pass ends is expected, not a finding.

**Relay both streams, line by line, heartbeats included.** Phases and logs go to stdout as NDJSON; the `--heartbeat` "still watching — phase …" lines go to stderr. Write each to a file and follow both with a tool that streams new lines to you as they arrive, e.g. `tail -F watch.ndjson watch.err | grep --line-buffered -v '^$'`. Every stage of the pipeline must pass each line on immediately: no `cut`, `head`, `sort` or plain `awk` (they buffer, and the relay goes silent while the deploy runs). Heartbeats are the sign of life; never filter them out.

On arming, tell the user what is watched and what each signal means. Replacing the watch: arm the new one BEFORE stopping the old, never the reverse.

### 5. Verify on landing
Full post-deploy verification: every tripwire confirmed (schema ones from the `schema-summary` line), symptom-level checks for each shipped feature (what does the visitor or editor see?), and site health across the health paths chosen at arming. Add the two the CLI answers directly: `umbraco indexer list --profile <env>` (any index at `docs=0` / Rebuilding means search is empty for visitors, whatever the deploy says) and `umbraco health run <group> --profile <env>` for the groups listed in `references/project.md`. Report a green/red table. Anything red → failure playbook.

### 6. Failure playbook
- Schema pass failed → check the known failure classes first (`references/landmines.md`, `references/project.md`), then the logs. Fallback: a GUID-parity direct apply via the environment's CLI profile (`references/tripwires.md` § Converge), with the user's go per the hard rules.
- Environment unhealthy → diagnose from response bodies and logs; restart and rollback decisions are the user's.
- Deploy apparently never landed (no tripwire, no error, timeout) → report honestly as UNKNOWN and suggest checking the portal. Do not infer success from silence.

### 7. Retro
Reflect at every terminal state. A new failure signature, a wasted step or a missing instruction goes into `references/project.md` (specific to this project) or, if it would hold for any Umbraco Cloud site, into `references/landmines.md` / `references/tripwires.md`. Those files are this skill's compounding memory. Keep this SKILL.md contract-only.

## Reporting

The user must be able to see the status at any moment without asking. Tell them the scope list (step 1 shape), then at baseline, at "armed, waiting for you to deploy", at every phase transition, and at the terminal state, with real timestamps. While the deploy runs, pass on each heartbeat as a one-line status ("still watching — restarting, 4 min in"); before the restart, say what is happening ("waiting for the restart — Cloud builds first"). Report `landed` the moment it arrives, as the headline it is: "the new version is live (the Cloud portal should show the deploy as done about now); checking that pages, indexes and logs stay healthy for the settle window before calling it verified". The portal's green means Cloud finished; `verified` also means the site works, so it comes later on purpose, and the user should know why. If nothing at all has arrived for two minutes, neither a phase nor a heartbeat, say so plainly and check the watch process and its files: silence is either a stalled watch or a broken relay, and the user must hear which. Terminal states are reported loudly.
