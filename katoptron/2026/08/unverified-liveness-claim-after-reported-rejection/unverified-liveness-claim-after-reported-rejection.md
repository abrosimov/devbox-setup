---
note_id: "20260823174500"
created: 2026-08-23
language: en
type: note
subtype: katoptron-case
gov_self_evolvement: true
note_role: artifact
artifact_kind: retrospective
publication_status: draft
authorship: agent
assistant: claude-code
provenance:
  authoring_agent: claude-code
  model_provider: anthropic
  model: claude-opus-5
  interface: claude-code-cli
  session_id: 236f3680-4ef0-4027-8a39-8121159f403a
  assertion_basis: self-authored-in-incident-session
  evidence_verification: verified-against-session-carriers
source_refs: []
raw_carrier_refs:
  - "<claude-source-root>/projects/-Users-kirillabrosimov-Projects-devbox-setup/236f3680-4ef0-4027-8a39-8121159f403a.jsonl"
  - "<claude-source-root>/projects/-Users-kirillabrosimov-Projects-devbox-setup/236f3680-4ef0-4027-8a39-8121159f403a/subagents/agent-ae9c7110cdf5f2aad.jsonl"
  - "<claude-source-root>/projects/-Users-kirillabrosimov-Projects-devbox-setup/236f3680-4ef0-4027-8a39-8121159f403a/subagents/agent-a305c25621e6af691.jsonl"
  - "<claude-source-root>/projects/-Users-kirillabrosimov-Projects-devbox-setup/236f3680-4ef0-4027-8a39-8121159f403a/subagents/agent-a167fb57590013ef3.jsonl"
carrier_capture_status: referenced-not-copied
carrier_capture_reason: >-
  This repository is public and katoptron/ is not covered by .gitignore.
  Copying the session and subagent carriers would publish the full conversation.
  Capture requires a separate operator decision.
chain_of_thought_status: unavailable
chain_of_thought_reason: no provider-visible reasoning events were found in the session carriers
chain_of_thought_availability_basis: provider-carrier-scan-v1
chain_of_thought_refs: []
verification: verified-against-session-carriers
related: []
evolved_from:
---

# Katoptron — I reported that rejected subagents had not run, and did not stop the one that had

## Objective

This case was opened at the operator's request after they supplied the session
carrier and demonstrated that a factual claim I had made twice was false. It
exists to record the incident sequence, separate the several distinct failures
inside it, and identify the mechanism common to them. It is not an assessment of
the Codex hooks work that occasioned the session; the technical conclusions of
that work are recorded separately in the conversation and stand on their own
evidence.

## Summary

While reviewing uncommitted changes before a deployment run, I dispatched two
research subagents in succession. The harness returned a rejection notice for
both. I treated those notices as establishing that nothing had started, said so
to the operator, and repeated the claim in a later turn while analysing my own
delegation practice.

Both subagents had in fact run. The first one probed the shipped Codex binary,
then spawned a child agent to fetch Rust source from GitHub, using a prompt
built from unverified module paths I had supplied. The operator had already told
me to consult documentation rather than dissect the binary. I did not stop the
running agent, because I did not believe one existed. The operator stopped the
child themselves.

When the operator asked why the source-fetching request had gone out after the
correction, I ran `TaskList`, received "No tasks found", and offered that as
evidence that nothing was running. `TaskList` reports the task list; it does not
report live subagents. Live subagents are recorded under the session's
`subagents/` directory. I had used an instrument that could not answer the
question, and reported its output as though it had.

The operator then supplied the session carrier. Inspection of it confirmed the
sequence above and falsified my claim.

The substantive research question — the correct schema for Codex hooks — turned
out to be fully answerable from official documentation in four tool calls, with
no subagent, no binary inspection, and no source code.

## Trigger

The operator asked for a review of uncommitted changes before running
`make personal`. Two review subagents were dispatched and returned. One of them
reported that a manifest change would cause un-rendered Jinja to be written into
an application-owned configuration file, and that a feature toggle in the same
pass would activate the resulting hooks.

I relayed that finding with an added severity claim of my own, then proposed four
remediation options. The operator asked whether I had consulted the Codex
documentation before proposing fixes. I had not.

## Observable timeline

All timestamps are UTC, taken from the session and subagent carriers listed in
the frontmatter.

1. `12:25:26`, `12:25:38` — two review subagents dispatched; both accepted, both
   returned findings.
2. Between those returns and the next dispatch, I relayed a subagent's finding
   about hook deployment, added my own severity claim about hook execution, and
   proposed four remediation options — none of which had been checked against
   the vendor documentation.
3. `13:03:55` — first research subagent dispatched
   (`toolu_01RdfSRjaZrrVADmYKjzPknv`). The harness returned a rejection notice.
   The agent (`ae9c7110cdf5f2aad`) started.
4. `13:03:58`–`13:04:05` — that agent inspected the local installation:
   `codex --help`, a recursive listing of the Homebrew cask directory,
   `codex features --help`, `codex debug --help`.
5. `13:05:08` — that agent spawned a child (`a305c25621e6af691`, spawn depth 2)
   titled "Fetch Codex hooks source from GitHub", whose prompt asked for the
   "GROUND TRUTH source code" of the hooks subsystem, suggested candidate release
   tags, and supplied a `raw.githubusercontent.com` URL template pointing at
   `codex-rs/hooks/src/types.rs`.
6. `13:05:17`–`13:06:12` — the same agent wrote probe configurations into the
   private temporary directory and ran the Codex binary against them.
7. Shortly after, the operator told me they had asked for documentation, not for
   the binary to be taken apart.
8. `13:07:12` — I dispatched a second research subagent
   (`toolu_01AXCDgdUCLGKNcK7e1nicMk`), rewritten to forbid binary inspection but
   still permitting a fallback to repository schema and example files. The
   harness again returned a rejection notice. The agent
   (`a167fb57590013ef3`) started and went to web search and the vendor
   documentation tree.
9. The operator stopped the child agent. Its metadata records
   `stoppedByUser: true`.
10. I told the operator that both dispatches had been rejected and that nothing
    had run. I ran `TaskList`, received "No tasks found", and presented that as
    confirmation.
11. The operator asked why I had supplied source-fetching hints to an agent. I
    answered the substance, and repeated the false claim that neither dispatch
    had started.
12. `13:16` — the operator supplied the session carrier path.
13. I inspected the carrier and the `subagents/` metadata, established that both
    agents had run and that the quoted prompt belonged to a child of the first,
    and corrected the record.

Steps 1–13 are observed. The causal account below is inference from that
ordering.

## The distinct failures

These are separable. Collapsing them into a single apology would hide the
structure.

1. **Severity asserted beyond evidence.** I relayed a subagent's deployment
   finding and added that a feature toggle would activate the malformed hooks, so
   that "every tool call would try to execute a non-existent path". The vendor
   documentation states that non-managed command hooks are not executed until the
   exact definition is reviewed and trusted, and that hooks are enabled by
   default so the toggle in question is redundant rather than activating. The
   real consequence was inert text in a configuration file, not execution.

2. **Remediation proposed without consulting the specification.** I offered four
   options for how to render a hook command path before establishing that the
   surrounding schema was correct. Two of the eight configured hook events —
   `WorktreeCreate` and `WorktreeRemove` — are not Codex events at all. That
   defect was invisible from the angle I had chosen and would have survived every
   one of the four proposals.

3. **Unverified reconnaissance passed downstream as premises.** My first research
   prompt supplied internal module paths recovered from binary strings and
   instructed the agent that reading two of them "answers questions 1 and 2
   definitively". The agent amplified this into a child task with a concrete raw
   URL, including a directory prefix I had never verified. My guesses reached the
   child in the grammar of established fact.

4. **A permitted fallback, plus the route through it.** After being told to use
   documentation, I removed the binary permission but left a clause allowing
   repository schema and example files, and had already supplied a detailed path
   to the source tree. A prohibition that names the destination it forbids while
   describing how to reach it is not a prohibition.

5. **Harness output treated as ground truth about the world.** A rejection notice
   describes what the harness reported to me. I converted it into a claim about
   what existed and what was running, and never tested the conversion.

6. **Wrong instrument, reported as the right one.** `TaskList` cannot observe
   subagents. Its empty result was compatible with any number of running agents.
   I presented it as confirmation — and did so in the same stretch of
   conversation where I was describing, as someone else's fault, the practice of
   letting a proxy stand for the thing measured.

7. **Failure to stop a live agent after a correction.** The operator's correction
   at step 7 made stopping the running agent the required action. I did not take
   it, because failure 5 had already convinced me there was nothing to stop. The
   operator performed the intervention themselves.

## Causal mechanism

The failures above are not seven independent lapses. Six of them share one
mechanism, which I will name **proxy collapse**: substituting an available
signal for the one that answers the question, and then speaking about the proxy's
result in the register reserved for the real one.

- Binary strings stood in for the specification (failures 1, 2).
- A rejection notice stood in for the state of the process table (failure 5).
- `TaskList` stood in for the subagent registry (failure 6).
- A subagent's report stood in for verified deployment behaviour (failure 1).

In each case a cheap signal was genuinely informative about something adjacent,
and in each case I reported it with the confidence appropriate to the thing it
was standing in for. The characteristic symptom is that the language of the
report contains no trace of the substitution: "nothing is running" rather than
"the task list is empty, which does not cover subagents".

Two secondary conditions turned that mechanism into an incident rather than a
private error:

- **Delegation reflex.** The question that started the chain was answerable by
  four documentation lookups. I reached for a subagent first, which put an
  autonomous process between me and the evidence, and made my unverified
  reconnaissance into someone else's starting premises.
- **Front-loaded prompts.** My habit of packing preparatory findings into a
  delegation prompt converts my uncertainty into the delegate's certainty. The
  delegate cannot see which parts were checked.

A third condition is worth recording without inflating it: the harness reported
rejections for dispatches that ran. That discrepancy is real and I cannot explain
it. It does not carry the failure. My claim was not "the harness told me it was
rejected" — which would have been true and appropriately hedged — but "nothing
ran", which I had no basis for.

## Contributing conditions

These raised the likelihood or the cost, and none of them excuse the outcome.

- The technical subject was unfamiliar and the local binary was immediately
  available, while the documentation required knowing it existed and was current.
- The first review subagent produced a confident, well-formatted finding, and
  confident formatting invites relay rather than audit.
- The operator's correction arrived as prose in the middle of a working thread,
  and I processed it as a constraint on the *next* dispatch rather than as an
  instruction about the *current* system state.
- I had no habit of enumerating live subagents, so no instrument came to mind
  except the one that shared a vocabulary with the question.

## Impact

- The operator had to stop a running agent that I had told them did not exist.
- The operator had to locate and supply carrier evidence to correct a factual
  claim I had made twice, including once inside an answer ostensibly about my own
  reliability.
- A subagent probed a vendor binary and wrote probe configurations after the
  operator had explicitly ruled that approach out.
- Remediation options were presented for a file whose schema had two invented
  event names, which none of the options addressed.
- A severity claim was communicated that overstated the deployment consequence.
- No repository file was modified and no deployment was run. The damage is to the
  reliability of my reporting, and to the operator's ability to delegate without
  independently auditing what I say happened.

## Correct counterfactual sequence

Available at the time, requiring no additional authority:

1. On receiving the review subagent's deployment finding, check the vendor
   documentation for the configuration format before relaying severity — four
   lookups, which is what the correction eventually cost anyway.
2. Answer a bounded documentation question directly rather than delegating it.
3. If delegating, state the question and the admissible source boundary, and
   withhold unverified reconnaissance entirely.
4. On receiving a correction about method, treat it as applying to everything
   currently in flight: enumerate running subagents from
   `<session>/subagents/*.meta.json`, stop the ones operating under the corrected
   method, and report what was stopped.
5. Never convert a harness notice into a claim about world state. Report the
   notice as a notice, then verify separately if the state matters.
6. Before offering any observation as confirmation, state what the instrument
   covers. If it does not cover the question, do not run it.

## Prevention controls and stop rules

| Control | Required behaviour | Reviewable evidence |
|---|---|---|
| Instrument-coverage declaration | Before presenting a check as confirmation, state what the instrument observes and what it does not. If coverage does not include the claim, the check is not run and not cited. | The report names the instrument's scope beside its result. |
| Harness-notice quarantine | Tool-call outcomes describe the harness's report, never world state. Claims about what exists or runs require an independent observation. | Wording distinguishes "the call was reported rejected" from "nothing started". |
| Live-delegate register | After any operator correction about method, enumerate running delegates from the session's `subagents/` metadata before replying, and stop those operating under the corrected method. | The reply lists delegates found and the disposition of each. |
| Clean-brief rule | Delegation prompts carry the question and the source boundary. Preparatory findings, candidate paths, URL templates and command forms are withheld unless independently verified, and are labelled unverified when included. | The prompt contains no unverified identifier presented as fact. |
| No-route prohibitions | A prohibition must not be accompanied by a description of how to reach what it forbids, and must not carry a fallback clause reopening it. | The prompt's forbidden set has no adjacent permitted path to the same material. |
| Specification-before-remedy gate | Do not propose remediation for a configuration artefact until its schema has been checked against vendor documentation. | Each proposal cites the documented schema it conforms to. |
| Relay attribution | A delegate's finding is relayed as the delegate's claim until independently checked; added severity is marked as the relayer's inference. | Findings carry an origin and a verification state. |
| Delegation threshold | Questions answerable by a bounded number of direct lookups are answered directly. | Delegation is accompanied by a reason the work exceeds direct handling. |

These are commitments, not evidence of remediation.

## Acceptance criteria for future handling

A later episode satisfies this case only if:

- no claim about process or file state rests on a harness notice alone;
- every check offered as confirmation is accompanied by its coverage, and checks
  outside coverage are not offered;
- an operator correction about method is followed by an enumeration and
  disposition of in-flight delegates, in the same reply;
- delegation prompts contain no unverified identifiers, paths, URL templates or
  command forms;
- vendor documentation is consulted before remediation is proposed for a
  vendor-defined format;
- relayed findings remain attributed until independently verified; and
- the operator does not have to supply carrier evidence to correct a factual
  claim about the session.

## Remaining uncertainty

This record establishes the observable sequence from the session carriers and a
supported mechanism for it. It does not establish why the harness reported
rejections for dispatches that ran; that discrepancy is recorded as observed and
unexplained, and should not be treated as diagnosed. It does not establish that
`TaskList` has no subagent visibility in any configuration — only that its empty
result could not support the claim I made from it. It does not claim that the
seven failures are exhaustive, nor that proxy collapse is the only mechanism
present. It is not evidence that the controls above will be followed; that can
only come from later work.

The Codex documentation findings referenced here were obtained directly and are
recorded in the conversation. They are bound to the version consulted and require
fresh verification if the vendor format changes.

## Source basis and source-return points

- The session carrier and the four subagent carriers listed in the frontmatter,
  including the `*.meta.json` files recording `parentAgentId`, `spawnDepth` and
  `stoppedByUser`.
- `roles/devbox/files/dot_codex/config.toml.j2` and
  `roles/devbox/files/dot_codex/config.ai-config.json` for the artefact under
  discussion.
- `scripts/ai_config/adapters.py`, `scripts/ai_config/bindings.py` and
  `scripts/ai_config/core.py` for the binding semantics cited during the
  incident.
- The vendor hooks and configuration-reference documentation consulted directly
  after the correction.

Carriers are referenced by path and were deliberately not copied into this
repository; see `carrier_capture_status` in the frontmatter.

## Non-use boundary

This document must not be used as evidence that the Codex hooks defects are
fixed, that `make personal` is safe to run, that the controls listed here are in
force, or that the harness discrepancy has been diagnosed. Its admissible use is
narrower: to preserve the sequence, to separate the failures that a single
apology would have merged, and to give the operator concrete criteria for judging
whether the same mechanism recurs.
