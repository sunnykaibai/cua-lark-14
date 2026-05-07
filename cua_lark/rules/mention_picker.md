# Mention Picker

Use:
- A real @ mention is a visible token or a selected picker option, not plain `@Name` text.
- Create tokens through visible mention UI: type only `@` or click the @ button, choose the person, then append remaining content.
- Preserve valid tokens when editing the rest of the draft.
- If a mention attempt leaves unrelated plain text, clear that failed draft and recreate the token.

Avoid:
- Typing `@Name message` as the whole message for mention tasks.
- Using `command a` or `backspace` after a valid token unless abandoning the full draft.
- Sending before the token and requested remaining content are present.

Batch:
- Batch stable mention setup actions; stop before selecting inside a picker that is not yet visible.
