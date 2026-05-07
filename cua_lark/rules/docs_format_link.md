# Docs Format And Link

Use:
- CRITICAL: NEVER use drag to select text for formatting. Drag is FORBIDDEN for partial phrase selection because it consistently over-selects or under-selects Chinese characters. Any drag action for text selection will produce incorrect results.
- The ONLY correct method to select a partial phrase for formatting (bold, highlight, code, etc.) is:
  1. ALWAYS start with command+f to search the exact target phrase in the document. This step is MANDATORY even if you think you can see the text — the find highlight gives you precise visual boundaries that are impossible to judge without it.
  2. Once the find highlights the target phrase (yellow/orange tint), close find with Esc.
  3. Now use the highlighted boundaries as visual guides: click precisely at the LEFT EDGE of the highlighted region (start of the first character).
  4. Shift+click at the RIGHT EDGE of the highlighted region (end of the last character) using: click(point='<point>X Y</point>', key='shift')
  5. Verify the selection covers exactly the target phrase (the floating toolbar should appear with the correct character count matching the number of characters in the target phrase).
  6. Apply the formatting once (command+b for bold, or the visible toolbar button).
- IMPORTANT: shift+click uses the click action with key='shift' parameter. Example sub-action: {"action": "click", "point": "<point>X Y</point>", "key": "shift"}
- NEVER skip the command+f step. Without the find highlight, character boundary targeting is unreliable for Chinese text.
- For links, select only the requested target text, open the link control or command k, enter the exact URL, and confirm.
- If target text is already visibly link-styled or a link popover shows the requested URL/domain, finish instead of reopening the dialog.
- For partial phrase formatting, format only the requested phrase and clear transient find/search highlighting before finishing.
- If a partial phrase formatting attempt spills onto neighboring text, repair the neighbor only: select the wrongly formatted neighboring text, remove the same style once, clear the selection, and recheck that the requested phrase stayed formatted.
- For bold/highlight/code tasks, judge from persistent document styling, not active text selection or find tint.
- Bold is a toggle, not a guaranteed set operation. For bold tasks, first decide from persistent document styling whether the exact target text is already bold.
- If the exact requested target text already appears visibly bold or thicker than adjacent normal body text, return finished. Do not select it again and do not press command-b or click B again.
- If the exact requested target text is not obviously bold, do not guess from a selected/highlighted state. First clear any transient find/search highlight or selection, then re-evaluate the persistent styling.
- Only after the target is clearly not already bold should you select exactly that text and apply bold with one method only: command-b once or the visible B toolbar button once.
- After applying bold once, clear transient selection or find/search highlighting with Esc or a nearby blank body click, then recheck the same text from persistent document styling. If the result is still ambiguous, stop and wait instead of toggling bold again.
- Use at most one bold toggle total per exact target span in a case. A second bold toggle on the same target is forbidden because bold changes are toggle actions and a second press can remove the formatting.

Avoid:
- NEVER use drag() to select text for formatting. This is an absolute prohibition. Drag ALWAYS produces incorrect character boundaries for Chinese text.
- NEVER batch a drag action followed by a format hotkey. Instead, break it into: click at start → shift+click at end → then format.
- Format the whole sentence when only a phrase is requested.
- Reselect or toggle the already-correct requested phrase when the only remaining problem is neighboring-text spillover.
- Treat search-result highlighting or selected text color as document formatting.
- Repeatedly drag-select the same already-bold target text.
- Toggle the same B control multiple times on the same selected text.
- Mix command-b and a visible B-button click for the same bold operation.
- Apply a second bold toggle anywhere later in the same case to "confirm" or "fix" the same target.
- Assume a selected or search-highlighted target is not bold just because its current selection tint makes the font look normal.
- Click link apply/confirm before the requested URL is visible in the input.

Batch:
- NEVER include drag as a sub-action in a batch for text selection.
- The correct batch for select+format is exactly: [{"action":"click","point":"<point>START</point>"},{"action":"click","point":"<point>END</point>","key":"shift"},{"action":"hotkey","key":"command b"}]
- Do not batch across link popovers or formatting menus that are not already visible.
