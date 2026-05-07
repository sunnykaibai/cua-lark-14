# Docs Exact Span

Use:
- For local text span operations, operate only on the exact requested target span.
- Exact span includes every requested character: Chinese/English punctuation, quotes, spaces that are part of the quoted target, hyphens, digits, colons, and suffix IDs.
- For insertion after an anchor sentence or paragraph, the insertion point must be after the whole visible sentence including trailing punctuation such as `。`, `.`, `：`, `；`, `！`, or `？`. Do not place the caret before the sentence-final punctuation.
- If a sentence-final punctuation mark is pushed to its own line or separated from the original sentence after an edit, treat it as a boundary error and repair it before finishing.
- Apply this to formatting, links, replace, delete, copy, cut, paste, move, and comment tasks when the instruction names a specific text, phrase, word, short sentence, or local span.
- Before applying the edit, visually confirm the selection begins and ends on the requested text.
- If the selection boundary is uncertain, clear the selection and use document find or a more precise selection route that is available in the current case's allowed-action list before applying the edit.
- For comment/annotation tasks, once the exact target span is visibly selected and a floating toolbar is visible, do not drag-select the same span again. Use the visible comment/annotation icon in that toolbar as the primary path; in Feishu Docs this is more reliable than a right-click context menu.
- For comment/annotation tasks, do not choose right-click as a fallback just because the span is selected. If the floating toolbar comment icon is not visible or not clickable, clear the selection once and reselect the exact span to reveal the toolbar, or use another visible top/inline comment control if one is clearly available.
- After the local span edit, clear transient find/search highlights, text selection, and floating toolbars before finishing, unless a visible popup is itself required evidence such as a link URL popover.
- Finish only from persistent document evidence: the exact target span has the requested style/link/edit, and surrounding text remains intact.
- Final-state hygiene is part of correctness: clear unnecessary active text selections, find highlights, slash menus, and transient toolbars before finishing unless that transient UI is explicitly required evidence.

Avoid:
- Omit punctuation from the requested span, such as Chinese colons, quotes, hyphens, digits, or trailing case-id characters.
- Split a sentence-final punctuation mark away from its anchor sentence during insertion or structure creation.
- Select the whole sentence, whole paragraph, nearby spaces, neighboring words, or only the case-id anchor unless that is exactly the requested target.
- Treat search-result highlighting, blue selected text, or a floating toolbar as persistent formatting.
- Treat an active selection highlight as proof of bold/highlight/link formatting.
- Repeat drag-selection of the same already highlighted span when the floating-toolbar comment path is available.
- Use right-click as the normal Docs comment path.
- Modify adjacent context text to make dragging easier.
- Repeat the same local edit after the requested persistent state is already visible.

Verify:
- PASS only when every requested character in the local target span is preserved or modified as requested.
- FAIL if punctuation or suffix characters are visibly missed.
- FAIL if anchor sentence punctuation is visibly separated onto another line by the operation.
- FAIL if only part of the requested span is modified.
- FAIL if neighboring text that was not requested is also modified.
