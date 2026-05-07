# IM Chat

Use:
- Treat real chat bubbles as live message objects; conversation-list snippets are previews.
- Keep conversation scope separate from sender identity.
- Inspect the newest task-relevant live message and the composer draft separately.
- For send/create/change tasks, use successful current-run history plus the newest live object; older pre-existing matches are weak evidence.
- After a successful send, inspect/navigate to the latest message area before starting another draft.
- For replies, marks, and reactions, operate on the concrete live bubble and its visible toolbar/menu state.

Avoid:
- Finishing from an arbitrary older match, conversation-list preview, or text inside an attachment preview.
- Falling back from reply/mark/reaction/share tasks to ordinary explanatory text.
- Re-composing when a successful send happened but the latest message is merely off-screen.

Batch:
- Batch stable composer/send/chat controls only while later targets remain visible and unchanged.
