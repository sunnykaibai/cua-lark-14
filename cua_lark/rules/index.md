# Rule Index

This index is intentionally compact. The runner can expose it to a future rule selector before loading full rule text.

| Rule | Description | Path |
| --- | --- | --- |
| `feishu_shell` | Feishu/Lark desktop shell, window visibility, global overlays, generic popups. | `cua_lark/rules/feishu_shell.md` |
| `live_object` | Distinguish real live UI objects from objects depicted inside screenshots, cards, images, or previews. | `cua_lark/rules/live_object.md` |
| `composer` | Text composer state, stale drafts, current-task drafts, text entry, and send completion. | `cua_lark/rules/composer.md` |
| `im_chat` | Chat bubbles, newest task-relevant outgoing message, replies, marks, reactions, and history matching. | `cua_lark/rules/im_chat.md` |
| `emoji_picker` | Emoji picker visibility, requested emoji selection, and emoji send completion. | `cua_lark/rules/emoji_picker.md` |
| `mention_picker` | Real @ mention token creation and mention picker behavior. | `cua_lark/rules/mention_picker.md` |
| `message_operations` | Reply, mark, and emoji reaction operations on real live chat bubbles. | `cua_lark/rules/message_operations.md` |
| `conversation_ops` | Conversation-list unread, mark, and completed operations on conversation rows. | `cua_lark/rules/conversation_ops.md` |
| `search_find` | Generic search/find flow: use product search before scroll scanning when locating target content. | `cua_lark/rules/search_find.md` |
| `attachment_share` | Local attachments, images, cloud documents, cards, share/send popups, and document search share flows. | `cua_lark/rules/attachment_share.md` |
| `rich_text` | Rich text composer formatting such as bold messages and formatted send completion. | `cua_lark/rules/rich_text.md` |
| `screenshot_overlay` | Screenshot overlay/menu/selection toolbar detection and visual recovery. | `cua_lark/rules/screenshot_overlay.md` |
| `docs_shell` | Feishu Docs surface, document entry/open/current-document state, browser chrome avoidance, and Docs popups. | `cua_lark/rules/docs_shell.md` |
| `docs_body_edit` | Docs body editor focus, text insertion, idempotence, local text paste, and title/body separation. | `cua_lark/rules/docs_body_edit.md` |
| `docs_structure` | Docs headings, lists, task lists, quote/code/table/divider structure creation and verification. | `cua_lark/rules/docs_structure.md` |
| `docs_search_navigation` | Docs document-scoped find, scrolling, outline/目录, sidebar/recent navigation, and dirty-data move recovery. | `cua_lark/rules/docs_search_navigation.md` |
| `docs_format_link` | Docs link creation, partial phrase formatting, bold/highlight/code styling, and find-highlight avoidance. | `cua_lark/rules/docs_format_link.md` |
| `docs_exact_span` | Docs exact local text-span boundaries for punctuation-safe formatting, links, replace, delete, copy, move, and comments. | `cua_lark/rules/docs_exact_span.md` |
| `docs_share_permission` | Docs share dialog, collaborator/permission state, inspect-only sharing tasks, and success toast evidence. | `cua_lark/rules/docs_share_permission.md` |
| `docs_local_material` | Local Markdown/text material paste into Docs, snippet bounds, agenda bullets, and material-token use. | `cua_lark/rules/docs_local_material.md` |
