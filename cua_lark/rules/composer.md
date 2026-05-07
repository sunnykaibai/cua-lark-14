# Composer

Use:
- Inspect the visible composer before composing.
- A covered composer may still preserve hidden draft text.
- Preserve valid current-task text, mention tokens, quotes, emoji, and requested attachments.
- If desired content is in the composer but not sent, continue the missing step instead of retyping.
- After a successful composer click, type next if no popup, error, or unrelated draft is visible.
- For plain text/text+emoji tasks, do not send unrequested attachments.
- Clear unrelated stale drafts, emoji-only leftovers, image/screenshot/file previews, stale file paths, or failed partial text before starting.

Avoid:
- Repeat-click the same composer only because the caret/focus is not obvious.
- Clear or overwrite valid mention tokens, reply quotes, requested emoji, or requested attachments.
- Retype or resend current-run content unless the screenshot shows a send failure or unsent draft.

Batch:
- Batch stable composer actions such as focus, clearing stale draft, typing text, and clicking a visible unchanged toolbar/send control.
