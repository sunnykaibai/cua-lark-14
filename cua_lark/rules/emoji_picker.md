# Emoji Picker

Use:
- An open picker may cover but preserve composer draft text.
- Resolve positional emoji requests from selectable live picker items, not images/previews.
- Select the emoji requested by the user when it is visible.
- Carry forward successful typed-draft history unless the screenshot contradicts it.

Avoid:
- Retype desired text only because the picker covers the composer.
- Select emoji-like content inside screenshots, cards, or image previews.

Batch:
- Opening the emoji picker may be the final sub-action of a batch; actions inside the newly opened picker wait until it is visible.
- If the picker is already open and the send control is visible and stable, batch `select requested emoji -> send`.
