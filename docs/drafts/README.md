# Draft scaffolds (quarantined)

These files were originally committed under `honeypot/challenge/` and
`honeypot/fingerprinting/` with a `.py` extension, but their contents are
Markdown design notes wrapping early draft code. They were **not imported by
anything** in the live application, and the code inside references modules that
do not exist in the repo (`fingerprint_db`, `challenge_session`,
`challenge_metrics`, `browser_fingerprint`, `network_fingerprint`,
`device_fingerprint`, …).

The actually wired-up implementations are:

- `honeypot/challenge/challenge_api.py`
- `honeypot/fingerprinting/fingerprint_api.py`

These drafts are preserved here as reference for ideas not yet integrated
(e.g. `StringManipulationChallenge`, `GraphProblemChallenge`,
multi-signal bot capability classification). They are intentionally `.md` so
they no longer break `ast`/lint/test collection. Recover the original `.py`
form from git history if needed.
