# Feishu Shell

Use:
- Identify the live Feishu surface: IM, Calendar, Docs, Search, Share, picker, modal, menu, or overlay.
- If the current screenshot is not on the target surface, recover to Feishu with the simplest visible host action first:
  1. If any live Feishu sidebar, tab, or window is already visible, use that visible Feishu host as the starting point.
  2. If Feishu is visible but not already on the target surface, stay within the visible Feishu host and identify the relevant entry from the current screenshot and task.
  3. If Feishu is not visible at all, use one visible app-launch action to open or activate Feishu, then continue from the visible Feishu host.
  4. Only when no Feishu surface is visible at all should a launcher fallback such as Spotlight be used, and it should be used once.
- If a popup/menu/picker/overlay is visible, decide from that state before acting on covered controls.
- Continue from an already-open task-relevant popup instead of reopening it.
- Close non-task blocking overlays with the least disruptive visible action, usually `hotkey(key='esc')`.

Avoid:
- Click controls that only appear inside embedded screenshots, images, cards, or attachment previews.
- Reopen a search, picker, or popup if the same useful state is already visible.
- Wander through unrelated apps, web pages, or generic search results to locate Feishu when a visible Feishu surface or a direct app-launch path exists.

Batch:
- Batch visible stable shell/popup actions when they do not depend on a newly opened surface.
