"""Stage 7 — generate the draft from the composed system prompt."""

from __future__ import annotations

from .common import FIXTURES, OPENAI_MODEL, OUT, openai_client, source_for

USER_INSTRUCTION = (
    "Write the article. 700-900 words. Markdown, with an H1 and H2 sections. "
    "Follow every rule in the system prompt."
)


def run(system_prompt: str) -> str:
    if source_for(7) != "live":
        return (FIXTURES / "draft.md").read_text()

    response = openai_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": USER_INSTRUCTION},
        ],
    )
    draft = response.choices[0].message.content
    (OUT / "draft.md").write_text(draft)
    return draft
