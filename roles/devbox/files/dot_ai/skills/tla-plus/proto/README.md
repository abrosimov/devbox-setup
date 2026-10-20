# Proto contracts of the tla-plus skill

| File | Contract |
|------|----------|
| `apalache/itf/v1/itf.proto` | Typed model of Apalache's ITF counterexample files, the target of a converter |
| `apalache/itf/v1/itf_vectors.txtpb` | Conformance vectors the converter reproduces; the drift detector for new Apalache releases |

Checks: `buf lint` here; `buf breaking --against <previous>` before a change to a message lands.
A project that reads counterexamples copies `itf.proto` into its own proto tree under the same
package and keeps the vectors next to its converter tests.
