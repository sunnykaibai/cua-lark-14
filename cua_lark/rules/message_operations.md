# Message Operations

Use:
- Reply, mark, and reaction tasks target a concrete live chat bubble.
- For replies, create a visible reply/reference state before typing reply content.
- If search/find highlights a target message, operate that highlighted live message and its toolbar/menu.
- If the toolbar is missing, open the target bubble context menu from the updated visible state.
- For reactions, choose the requested emoji as a reaction on the target message, not as a new message.

Avoid:
- Falling back to normal composer text for reply/mark/reaction tasks.
- Typing reply content before a quote/reference block or reply mode is visible.
- Closing/searching/scrolling away when the highlighted target and operation controls are usable.
- Operating on screenshots, cards, thumbnails, previews, or older matching history.

Batch:
- Batch stable hover/context-menu actions; stop before acting inside a menu or picker that has not appeared yet.
