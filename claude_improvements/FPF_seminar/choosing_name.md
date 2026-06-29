---
tags: [claude-improvements, fpf-seminar, naming, katoptron]
seminar-iteration: 0
created: 2026-06-28
status: decided
decision: Κάτοπτρον (Katoptron)
---

# Choosing the project name — Κάτοπτρον

## The naming problem

The `claude_improvements/` catalogue — 36 files, ~4900 lines — analyses Claude Code's behavioural dysfunctions, traces them to 30 root causes across 6 causal layers, and proposes 150+ fixes. It needs a name that captures the project's character accurately enough to orient every future session.

## Selection criteria (FPF-informed)

Three FPF principles shaped the evaluation:

1. **A.7 (Strict Distinction)** — the name must separate the EntityOfConcern (Claude Code's behaviour) from the CharacteristicSpace (the analytical method). A name that conflates them would misdirect.
2. **A.6.B (Laws vs Work)** — the name should not imply the project can change model-internal behaviour (Layer A). It observes and mitigates.
3. **A.15 (Work)** — the name should suggest ongoing activity, not a one-shot artefact.

## Candidates evaluated

### 1. Ἀνάμνησις (Anamnesis) — recollection / patient history

- **Medical sense:** anamnesis = the diagnostic interview, patient history. The project collects Claude's "case history" (41 symptoms → 30 root causes → diagnosis).
- **Platonic sense:** recollection of innate knowledge. Claude already "knows" how to behave; configuration should help it remember, not overload it with 509 lines of rules.
- **Ecosystem link:** MNEMOSYNE_PERISTASEOS (memory of circumstances) → anamnesis as the return of memory. RC-06 (no working memory) is literally about amnesia.
- **Central thesis:** the problem is not ignorance but forgetting. The cure is not adding rules but restoring attention to existing ones.
- **Weakness:** implies the project is primarily about memory. It is broader — it also diagnoses, prescribes, and audits its own prescriptions.

### 2. Ἔλεγχος (Elenchus) — Socratic cross-examination

- **Method:** systematic refutation through questions. The catalogue cross-examines each Claude behaviour: "You claim you ran tests. But tool-call history has no pytest. Explain." (RC-24).
- **Recursion:** the FPF diagnostic is an elenchus of the catalogue itself: "You diagnose bloat. But you prescribe 25 new skills. Explain." (D1).
- **Tone:** confrontational but constructive. Not a mirror — an interrogation. Not medicine — verification.
- **Weakness:** names the method, not the object. The project is not only cross-examination; it also builds fix proposals. Elenchus tears down — this project also builds up.

### 3. Φάρμακον (Pharmakon) — remedy that is also poison

- **Derrida (Plato's Pharmacy):** writing is pharmakon for memory — it helps remember but weakens memory itself. Configuration is pharmakon for Claude — it helps follow rules but consumes attention budget.
- **D1 — exact hit:** diagnosis says 509 lines → attention overflow. Prescription adds 25 skills + 15 output-styles + 10 hooks. Medicine = poison. Pharmakon in its purest form.
- **Risk:** negative connotation. In later Greek — "witchcraft". But the paradox is the project's essence.
- **Weakness:** captures the central paradox brilliantly but names the *tension*, not the *project*. Using "Pharmakon" as identity risks framing the work as inherently self-defeating rather than productive.

### 4. Κάτοπτρον (Katoptron) — mirror ✓ CHOSEN

- **Etymology:** κατά (down, against) + ὄπτομαι (to see) = "to look at oneself".
- **Metaphor:** Claude looks at its own reflection. Symptoms are distortions in the mirror. Root causes are the optics of the mirror. FPF diagnostic checks whether the mirror itself is curved.
- **Catoptrics:** the science of reflection. The project = catoptrics of Claude Code.
- **Noted weakness:** a mirror is passive — it reflects but does not cure. This project is both mirror and scalpel.
- **Rebuttal to weakness:** the scalpel work (fixes, hooks, skills) is downstream of the mirror. The catalogue's primary function is accurate reflection; the fixes flow from it. A mirror that also cuts is still, first, a mirror. The name captures the foundational act.

## Decision rationale

Katoptron was chosen over the other candidates because:

1. **Object, not method.** Anamnesis names the medical procedure; Elenchus names the dialectical method; Pharmakon names the paradox. Katoptron names the *thing the project is* — a reflective surface for self-examination. Methods and paradoxes are features of the mirror, not the other way around.
2. **Extensible.** "Catoptrics" as the science of reflection accommodates future work: new symptoms are new distortions; new FPF diagnostics check the curvature of the mirror; fixes are corrections to the optics.
3. **Fits the ecosystem.** AION_AUTOPOIESEON (self-creation) needs a self-reflective instrument. Autopoiesis without catoptrics is blind.
4. **The weakness is productive.** "Mirrors are passive" is a constraint worth holding. It reminds us that the catalogue's job is to reflect accurately. When fixes are proposed (the "scalpel"), they are evaluated against the mirror's image — not the other way around.

## See also

- [[seminar_timeline]] — seminar MOC
- [[11-fpf-diagnostic]] — first structural audit (pre-naming)
