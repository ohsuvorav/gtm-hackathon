# Connected call sources

Use this branch after viable Surfer gaps have been persisted. Retrieve one recording per run.

## Fyxer

Fyxer is connected separately from this plugin. Use the tools exposed by the current session and inspect their schemas before supplying arguments.

1. Use `find_recordings` to locate the title or identifier the user named.
2. Continue automatically only when the result identifies exactly one recording.
3. Ask the user to choose when multiple recordings match. Stop when none match or transcription is incomplete.
4. Call `get_transcript` for that recording only.
5. Save the returned transcript verbatim. Preserve speaker labels, timestamps, wording, and identifiers.
6. Run `save_source.py` with provider `fyxer`, the Fyxer recording ID, title, a stable source ID, and the staging transcript path.

Do not inspect email, contacts, memory, other recordings, or a repository transcript fixture to fill missing data.

## Other sources

A compatible source must support a bounded recording lookup and transcript retrieval. Map its provenance into `SourceDocument` and use the same `save_source.py` helper. When the user supplies a local file or pasted transcript, use provider `local` and the file path or a stable supplied identifier as `external_id`.
