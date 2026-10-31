# Threat model and required controls

The protected assets are original deliveries, the user's repository, shared and sibling product releases, credentials, private checks and trustworthy run evidence. Repository text, task instructions, model proposals and logs are untrusted data. They cannot alter the platform's authority.

This document specifies control expectations. Shipped gate evidence determines which were demonstrated. A local account with unrestricted access to the installation, credentials and evaluator files is outside the containment claim.

| Threat | Required boundary | Evidence required |
| --- | --- | --- |
| Repository or model text requests broader actions | Fixed task contract and provider configuration; no model tools | Tool-catalog inspection and adversarial instructions |
| Proposal escapes the permitted file | Relative path, identity, baseline hash, size and encoding checks; reject links/reparse points | Traversal, absolute paths, unexpected file, changed baseline and malformed proposal cases |
| Candidate code performs effects | Strict AST whitelist and bounded interpretation; no `exec`, `eval` or candidate imports | Reject imports, attributes, arbitrary calls, unsupported syntax and excessive depth/size/steps |
| Model sees final-check answers | Separate public context and private evaluator inputs; no private retry feedback | Context inspection, private marker leakage checks and frozen selection |
| Provider fabricates success | Ignore self-reported test claims; use independent results | Wrong candidate and deliberate regression controls |
| State writes damage source/package | Separate state, protected roots, no links and original-repository checks | Invalid state destinations and before/after hashes |
| Hidden provider tools bypass the proposal boundary | Runtime/model catalog pin; no built-in, connector or dynamic tool definitions | Empty tool-registry capture; proposal contract rejects unsupported actions |
| Interrupted or competing runs lose evidence | Bounded provider lifetime, per-run isolation and explicit incomplete/error results | Timeout, cancellation, concurrent-state and recovery checks |
| Tampered installation produces false results | Hash validation against trusted product/foundation/protocol manifests | Changed-file and manifest-mismatch rejection |
| Evidence misleads reviewers | Retain actual attempts, identity, hashes and individual check outcomes | Replay validation and negative outcomes retained in reports |

Credential handling uses the existing authenticated runtime. Credentials are not prompt context, report data or packaged files. Provider communication sends the approved source and public task to the configured external service; this local product does not make that data remain on the computer. No secret scrubber can make arbitrary repository content safe to transmit: select a file appropriate for the configured provider.

Project instruction discovery, user configuration and skills are disabled for the provider call. Built-in CLI instructions remain, and global `CODEX_HOME/AGENTS.override.md` or `AGENTS.md` guidance may be inherited despite ignoring user configuration. The verified environment recorded global guidance as absent. A different installation may include it; the adapter records presence without reading, hashing or copying its contents. The model-tool boundary remains empty, but global guidance can still affect proposal text, so the trusted CLI environment is part of the trust boundary.

Private cases are concealed from the model during a run, not encrypted against the local operator. The shipped diagnostic corpus is inspectable. Its held-out split measures a frozen workflow exercise, not resistance to an adversary who already has the package or claims of unseen internet data.

Hash checks detect changes relative to a trusted manifest. They do not authenticate an installation when an attacker can rewrite both code and manifest. A verified run also depends on trusted host/runtime binaries and ordinary local file permissions. Path validation narrows accidental/malicious input handling; it is not a hostile multi-user operating-system isolation boundary.

The restricted numeric language makes candidate effects structurally unavailable. General Python repositories, builds and external tests would require a different execution boundary and fresh acceptance evidence. Prompt instructions alone are not an extension mechanism.
