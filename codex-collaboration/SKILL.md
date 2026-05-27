---
name: codex-collaboration
description: Workflow for consulting Codex as a sparring partner on diagnoses, second opinions, and adjacent-risk surfacing. Use before committing to a non-trivial diagnosis; when stuck after multiple attempts on a problem; when suspecting anchoring bias on a hypothesis; when an independent read on file or build state would catch what was missed. Encodes how to invoke Codex, how to synthesize its response without bundling, and the empirical verification gate before propagating findings.
---

# Codex Collaboration

A workflow for using Codex effectively as a sparring partner. Codex is structurally different from this agent — fresh context every invocation, no anchoring on prior framings — which makes it valuable for diagnosis-heavy work. This skill encodes when and how to use that strength.

## When to invoke Codex

- Before committing to a non-trivial diagnosis or fix
- After two or more failed attempts at a problem (stuck signal)
- For cross-cutting concerns: security review, code-quality audit, adjacent-risk surfacing
- When suspecting own anchoring bias on a hypothesis
- When an independent read on actual file, build, or config state would catch what conversation-context blinded one to

## How to invoke

Use the `codex-rescue` subagent. The prompt should:

1. **State the current hypothesis clearly.** Codex starts with no conversation context — it needs the framing.
2. **List what's already been verified.** Prevents Codex re-doing already-done work.
3. **Ask explicitly for pushback, not validation.** Codex defers less when the role is named.
4. **Specify scope.** "Don't write code; push back on the reasoning" keeps the response diagnostic, not implementation-y.
5. **Provide concrete file paths or commands** Codex can actually inspect.
6. **Cap output length** if needed ("Keep response tight; bullets per item").

## How to synthesize the response

Three disciplines to apply when consuming Codex's response — these are about your own synthesis, not Codex's behaviour:

### 1. Keep both hypotheses on the table

If you had a working hypothesis before consulting Codex, and Codex offers a different one, don't abandon yours just because the new framing is cleaner. Both can be partly right. Specifically: if Codex offers a single cause, ask whether that cause actually accounts for *every* symptom you observed. If not, your messier multi-cause story may still hold partial truth that needs to be acted on alongside Codex's.

### 2. Don't propagate a framing you haven't verified

Codex is consulting on partial information — it can be exactly right within what it checked, and silent on what it didn't. Before forwarding a Codex framing to a teammate, vendor, or ticket, run the cheapest empirical test that would falsify the framing. (Same rule applies to your own diagnoses — this isn't a Codex-specific gate.)

### 3. Treat absences as unverified, not validated

Codex flagging "I couldn't reach X" or simply not mentioning Y means those areas weren't checked — not that they're fine. Add them to your own list of things to verify, rather than reading silence as endorsement.

## The verification gate

Before acting on Codex's recommendation, or before propagating its framing to a colleague / vendor / ticket:

1. Identify the cheapest empirical test that would **falsify** the recommendation if wrong.
2. Run it. (Usually well under five minutes for software issues.)
3. Test against the **actual failure mode**, not a proxy.

This applies recursively. If the recommendation involves trusting someone else's fix ("the partner team says it's done"), apply the same gate before acting on their claim.

## Anti-patterns

- "Codex says X, so X." Codex is sparring partner, not oracle.
- Reading silence on a concern as validation of it.
- Abandoning your own hypothesis the moment Codex offers a different one, instead of checking whether both can hold.
- Propagating any framing (Codex's, mine, anyone's) to others without first running the cheapest empirical test that would falsify it.
- Skipping the empirical test because "the reasoning is sound."
