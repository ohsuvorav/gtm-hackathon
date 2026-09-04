---
name: generate-customer-brand-demo
description: Given a customer domain, duplicate the Paper.design Slack mockup template and reskin it with that customer's brand — icon + primary color. Never touch the template itself.
---

Regenerate the branded demo asset for one customer domain, without ever mutating the source template.

**Fixed template (this hackathon's Paper file — do not change unless the user says so):**
- File ID: `01KZY2A72SFQH52ZSZ7YRZNSEZ`
- Template artboard to duplicate: `TF-0` ("2nd slack")
- Inside it: `TK-0` = background/primary-color rectangle, `UX-0` = workspace icon frame (top-left), `15G-0` = avatar image leaf

**Phase 1 — Extract the brand from the live domain**
- Navigate to `https://<domain>/` with a real browser tab (claude-in-chrome), not `curl`/`fetch` — brand CDNs return a bot-challenge HTML page to non-browser requests, not the asset.
- Query `header svg, nav svg, a[href="/"] svg` on the page. Pick the match with a wide viewBox (roughly 3–4:1 aspect ratio) — that's the wordmark, not a nav icon.
- Read `.outerHTML` via `javascript_tool`. If longer than ~800 chars, pull it in two `.slice()` calls — the tool truncates single large returns.
- **Never** try to `btoa()`/base64 it or dump raw `fetch().text()` output — both get blocked as suspected credential/cookie exfiltration. Plain sliced text is fine.

**Phase 2 — Make the asset standalone**
- Write the SVG to a local scratch file.
- Replace any `var(--...)` in `fill` with a literal hex (the page's own CSS vars won't resolve outside its stylesheet) — use black unless the user names a color.

**Phase 3 — Duplicate the template (never edit `TF-0` directly)**
- `duplicate_nodes({ nodes: [{ id: "TF-0" }] })`.
- Read the returned `descendantIdMap` for this run's new IDs of `TK-0`, `UX-0`, `15G-0` — they change every duplicate.

**Phase 4 — Reskin the duplicate**
- Background: `update_styles` on the new `TK-0` → `{ backgroundColor: "<brand hex>" }`.
- Icon + avatar: `write_html` mode `replace` on the new `UX-0` and `15G-0`, each with a 36×36 white rounded tile (`box-shadow: #E8E8E821 0px 0px 0px 1px, #00000014 0px 1px 3px`) containing `<img src="paper-asset:///<absolute local svg path>" style="width: 24px; height: 24px;">`.
- **Always** give the `<img>` an explicit pixel height — `height: auto` resolves to `0` and the asset silently disappears.
- **Never** pass a remote `url(https://...)` into `update_styles`'s `backgroundImage` — it creates a broken `.tmp` asset that never renders, regardless of source. Local file → `paper-asset://` is the only reliable write path.

**Phase 5 — Verify**
- `get_screenshot` on the new artboard ID. Confirm the icon renders (not a blank/broken tile) and the color applied.
- `finish_working_on_nodes`.
- Report back: new artboard ID + domain, template untouched.
