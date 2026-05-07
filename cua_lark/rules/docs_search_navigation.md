# Docs Search Navigation

Use:
- For finding text inside the open document, prefer command f or a visibly document-scoped find box.
- For document entry/open tasks, prefer the Feishu app/Docs cloud-document exact-title search as the default route. Use the cloud-docs content search box/top Docs search in the Feishu app entry surface, not the far-left Feishu global search box, a browser Docs home shortcut, or a recent-list shortcut.
- When the current surface is an already-open Docs document but the requested document is different, first return to the Feishu app/Docs cloud-document entry surface, then use that surface's document search. The editor-page top-right magnifier and browser Docs home are not the primary document-entry route.
- If replacing an old Docs search query with the exact target title produces no visible change, do not keep typing the same title. Refocus or clear the visible Docs search field once, then type again, or open the visible exact-title result if it is already shown.
- If the exact full document title is already typed in a visible Docs search field, visually identify and click the matching result with the exact title once. On the next screenshot, finish immediately if the opened document page shows the exact title. If the same popup/result remains, do not click that same result again as the immediate next action; wait once for navigation/loading evidence, then use Enter or another visible open affordance only if the same focused result is still present.
- If multiple exact-title results are visible, do not default to the first same-title row blindly. Prefer the result whose visible snippet, metadata, or surrounding context best matches the current case's unique anchor or expected document state; if one result clearly matches the current task better, choose that row once and then wait for navigation evidence.
- Use scrolling, outline/目录, sidebar, recent documents, or visible document entries only when they are document-scoped navigation or an exact-title fallback after the cloud-docs search route is unavailable or has clearly failed.
- If a target anchor is visible, operate from that visible evidence instead of searching again.
- From the Feishu Docs home/list/recent file table, do not open a requested entry document directly from a recent row by default. First use the cloud-docs search box with the exact full title. If search is unavailable or has clearly failed, use double-click on the middle of the exact title text as a fallback. Target the title text, not the icon, row edge, empty row space, time column, or a highlighted different row.
- After a document entry/open task reaches the target document page, do not reopen search or click the target title again; return finished.
- If a click on a visible exact-title row does not open the target document, do not return home or start a new search immediately; use the same row's clearer open gesture such as double-clicking the title text or pressing Enter while that row is selected. If the row is no longer visible because a non-target document opened, return home/list and use double-click on the exact target title next time.
- If document find reports zero matches for a source paragraph in a move task, recover as dirty shared test data only when the target paragraph is visible and the source is truly absent.

Avoid:
- Do not repeatedly click top-right global search when the task is document-scoped.
- Do not switch browser tabs as a substitute for exact-title Docs search in entry/open tasks.
- Do not use the far-left Feishu global search box as the main way to find a cloud document.
- Do not use the editor-page top-right magnifier as the main way to open another cloud document from inside a document.
- Do not open a requested cloud document from the recent list before trying the cloud-docs search box, unless search is unavailable or already failed.
- Do not use browser Docs home/search as the default entry route for non-browser entry cases.
- Do not press Enter before clicking a visible exact-title search result.
- Do not reopen search with `command k` after the exact full title is already visible in a Docs search field.
- Do not repeat click/click/double-click loops on the same document entry when a different route or wait is the next safer step.
- Do not click the same exact-title search result in two consecutive steps.
- Do not click the same exact-title search result again after already clicking it, waiting, and pressing Enter on that same result.
- Do not repeatedly click the same exact-title search result after it has already been clicked once.
- Do not single-click a Feishu Docs home/list/recent file-table row as the default open gesture.
- Do not click row icons, empty list space, date/time columns, or nearby highlighted rows when the goal is to open a specific document title.
- Do not repeatedly type the same full document title when the search field still shows the old query.
- Do not keep scrolling or searching after the target text is already visible and usable.
- Do not infer that invisible source text exists above or below after a clear zero-match result.

Batch:
- Batch focus/type/enter for a visible document find box when the query is known and the next target is the same stable field.
