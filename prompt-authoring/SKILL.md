---
name: prompt-authoring
description: Structural template and principles for authoring high-signal prompts to another model — typically Codex via the codex-rescue/codex-collaboration path, but the pattern generalizes to any agent handoff where you need diagnosis, second opinion, code review, or pre-loaded context. Encodes the mode header, task block, context dump, working hypothesis, deliverables, grounding rules, output contract, and action safety boundary. Use whenever you're about to write a non-trivial prompt to another model.
---

# Prompt Authoring

A well-structured prompt is the difference between getting a sharp diagnosis and getting prose. The model on the other end has no continuity of memory, no anchoring on your prior framings, and no idea what you've already ruled out. Your job is to pre-load its context, state a hypothesis it can refute, define the output shape, and constrain the action.

This skill encodes the structural template that works. Demonstrated primarily through Codex prompts (because that's the pairing where it pays off most), but the same pattern applies to any model-to-model handoff.

## When to invoke this skill

- Before consulting Codex via `codex-rescue` or the broader `codex-collaboration` workflow
- Before handing off to any subagent for diagnosis, review, second opinion, or scoped implementation
- Before authoring a standby briefing that pre-loads context for an upcoming event

Skip for trivial one-line queries. Use it whenever the request is complex enough that "help me with X" would leave the recipient guessing.

## The structural template

Use XML-style tags so the recipient sees explicit structure. Not all blocks are mandatory for every prompt — pick the ones that fit the situation. But the order matters.

### 1. Mode header (one line, no tag)

Open with role + intent in plain text. Sets the recipient's mode before they read anything else.

- `RESCUE REQUEST — production incident on X, diagnosis + recommended action needed. READ-ONLY.`
- `Sparring-partner second opinion (read-only, no edits). Independent review of [diagnosis | fix | architecture].`
- `STANDBY BRIEFING — [event] happening today. Not asking for action; acknowledge context for fast follow-up later.`
- `SCOPE CORRECTION — prior framing was wrong. Re-briefing with corrected facts.`
- `REVIEW REQUEST — code review pass on [scope]. Find what I missed.`

### 2. `<task>` block

Concrete ask + repo path + read/write scope. Two or three sentences max.

- ❌ "Help me figure out why the deploy failed"
- ✅ "Investigate why today's live deploy failed at the Umbraco Deploy 'Extracting Schema Files' step with error [DeploymentUpdateSiteExtensionUnableToStartUmbracoDeployExtraction]. Repo: /path/to/repo (READ-ONLY)."

### 3. `<context>` block

Salient state the recipient needs that isn't trivially derivable. Dump it with citations:

- File paths with line numbers
- Commit SHAs (and what changed in each)
- Exact error strings, timestamps, log excerpts (verbatim, not paraphrased)
- Affected PRs with their net effect
- Version numbers / config values
- Symptom inventory (what works, what doesn't)

Goal: the recipient shouldn't need to ask "what's the error message" or "which commit introduced this". If they need to read a file you've named, they can — but they shouldn't have to guess which files matter.

### 4. Working hypothesis (optional but recommended)

State what you think is happening, with evidence. Name suspects explicitly. Mark the prime suspect.

> "Working hypothesis: the package rename in PR #302 means `__type` references in artifacts authored before the rename point to types that no longer exist on live. *** PRIME SUSPECT. ***"

Gives the recipient a target to refute or refine. Without a hypothesis you get enumeration; with one you get force-ranking.

### 5. `<deliverables>` or `<questions>` block

Numbered list of what you want back. Be specific.

Example (deliverables — broad investigation):

1. Validate or refute the package-rename hypothesis. List offending files with `__type` strings, or say 'clean'.
2. Alternative hypotheses worth ruling out, ranked by likelihood with evidence.
3. Recommended recovery sequence with ordered steps.
4. Success vs masked-failure signals for post-retry verification.

Example (questions — targeted second opinion):

1. Is the diagnosis correct? Or is there another mechanism that better explains the symptom?
2. Is the fix sound? Any reason it would pass locally but fail in CI?
3. Adjacent risk: are nearby tests vulnerable to the same flake? Rewrite or leave?

### 6. `<grounding_rules>` block

The rules that keep the recipient honest. Adapt to context, but these are the recurring ones:

- Anchor every claim to a file path + line / commit / log excerpt actually read.
- If a claim can't be verified from the artifacts provided, label it explicitly as hypothesis.
- Don't invent internals, exception names, or platform behaviors. If unsure, say 'unverified' and propose how to check.
- Distinguish 'confirmed by inspection' vs 'inferred from symptom pattern' in every finding.
- Disagreement encouraged — find holes now, not in CI / not in prod.

Without these the recipient sometimes confabulates plausible-sounding internals. With them, they hedge appropriately or ask.

### 7. `<structured_output_contract>` or `<compact_output_contract>` block

Tells the recipient the response shape. Choose based on depth needed:

- `<structured_output_contract>`: full sections, ordered, dense — for deep investigations
- `<compact_output_contract>`: short labeled sections (≤6 lines each), one-line verdict — for second opinions

Example phrasing: "Return one structured response with these sections in order: 1. Hypothesis validation 2. Alternative hypotheses ranked 3. Recommended recovery sequence 4. Verification checklist 5. Open questions. Keep it dense and actionable. No filler."

### 8. `<action_safety>` block

What the recipient is allowed to do. Always include this.

- `READ-ONLY. Do not edit, stage, commit, or push. Do not run dotnet/npm/build/test commands.`
- `Read-only investigation. Propose changes but do not write them.`
- `Write-allowed within /path/X only. No changes outside this directory.`

Models default toward action. Constrain explicitly.

## When to use each mode header

- **RESCUE REQUEST**: production failure, debugging, "something broke, find the cause"
- **Sparring-partner second opinion**: you have a hypothesis you want pressure-tested
- **STANDBY BRIEFING**: pre-load context before an event so the recipient is primed for fast follow-up if something fails (most under-used pattern — try it before any risky deploy or refactor)
- **SCOPE CORRECTION**: your framing changed mid-investigation; spawn a fresh agent with corrected facts rather than trying to edit the prior session's understanding
- **REVIEW REQUEST**: code review pass on a specific change

## Core principles behind the template

1. **Pre-load the surface area.** The recipient's context is fresh every invocation. Dump salient state upfront so they don't waste turns asking or guessing.

2. **State your hypothesis first.** Open-ended produces enumeration. Specific produces force-ranking. Give them a target to refute.

3. **Encourage disagreement explicitly.** "Disagree freely", "find holes now not in CI", "refute or refine". Counteracts agreement-shaped output that LLMs default to.

4. **Cite everything.** File paths with line numbers, commit SHAs, error strings verbatim. No citations = no verification path.

5. **Label uncertainty.** Force the distinction between "I read this" and "I'm guessing this". Applies to both your prompt and the response.

6. **Constrain the output shape.** Section order, length limits, density. Otherwise you get prose where you wanted a list.

7. **Action safety upfront.** Read-only / scoped / write-allowed. Models default toward action; constrain explicitly.

## Anti-patterns

- **"Do you agree with my analysis?"** — produces agreement-shaped output. Reframe: "Refute this or find what I missed."
- **No citations** — the recipient can't verify, and you can't either. Always cite the evidence.
- **No output contract** — you'll get prose. State the shape.
- **No action safety** — the recipient may start writing fixes when you wanted diagnosis. Always declare scope.
- **Padding context with everything** — only dump what's relevant. If the recipient needs file X they can read it; they don't need its full contents in the prompt.
- **Open-ended "what do you think?"** — gives no target to refute. Always state a position the recipient can refine or reject.

## Pairing with other skills

- **codex-collaboration**: covers WHEN to invoke Codex and what to do with the response. This skill covers WHAT goes in the prompt.
- **pull-request-authoring**: same author-the-thing structural mindset, different artifact (PR bodies instead of agent prompts).
