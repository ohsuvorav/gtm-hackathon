# Connected call sources

Use this branch after viable Surfer gaps have been persisted. Retrieve one recording per run.

## Fyxer recording-name invocation

Fyxer is connected separately from this plugin. Use the tools exposed by the current session and inspect their schemas before supplying arguments.

The explicit invocation `$info-to-content:info-to-content <recording-name>` supplies one positional recording title. It is not transcript content and it is not a path.

1. Require a non-empty positional recording name.
2. Call `find_recordings` with `query` set to that recording name and `maxResults` set to `10`. Do not put the name into attendee, participant, date, or content-search compatibility fields.
3. Compare the returned recording titles with the requested name. Prefer a literal exact match; a case-folded, surrounding-whitespace-normalized title is also exact for resolution purposes. Do not automatically select a partial, semantic, attendee, summary, or recency match.
4. Continue automatically only when exactly one exact-title recording remains. Ask the user to choose when multiple exact-title recordings remain, showing enough metadata to distinguish them. Stop when none match or transcription is incomplete.
5. Call `get_transcript` for that recording ID only. Follow pagination until the full transcript is retrieved. A result with zero transcript segments is a clean stop, not a retry condition.
6. Save the complete returned transcript verbatim. Preserve speaker labels, timestamps, wording, and identifiers.
7. Run `save_source.py` with provider `fyxer`, the Fyxer recording ID, returned title, a stable source ID, and the staging transcript path.

Do not inspect email, contacts, memory, other recordings, or a repository transcript fixture to fill missing data.

## Other sources

A compatible source must support a bounded recording lookup and transcript retrieval. Map its provenance into `SourceDocument` and use the same `save_source.py` helper. When the user supplies a local file or pasted transcript, use provider `local` and the file path or a stable supplied identifier as `external_id`.
