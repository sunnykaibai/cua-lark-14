# Docs Shell

Use:
- Identify whether the current surface is an open Docs page, Docs home/list, document search, share dialog, permission panel, browser chrome, or embedded document content.
- For every Docs editing, formatting, linking, sharing, permission, find, drag, typing, or editor hotkey task, first confirm the current screenshot is a live Feishu/Lark Docs host surface before using Docs editor shortcuts or controls. This applies even when the instruction does not mention a document title and assumes a document is already open.
- A live Docs host surface means a real Docs editor/page/home/search/share UI is visible in the active app or browser host, not a screenshot, report, chat transcript, old result image, or embedded preview that only depicts Docs.
- If the screenshot shows a non-Docs Feishu surface, a report page, a chat/notes surface, or any embedded image of Docs, do not use command-k, command-f, command-b, drag, type, or toolbar controls as if they were live Docs controls. Recover to the Feishu app Docs/云文档 entry surface first.
- For every Docs edit/format/link/comment/share/material/provision task, first inspect whether the current screenshot is already the exact target cloud document. If it is the target document in browser Docs, operate there. If it is not the target document, do not continue browsing/searching inside the browser; recover through Feishu app -> 云文档/Docs.
- For Docs content-changing tasks with an explicit target document title, the execution host should be browser Docs. If the current screenshot is a Feishu desktop embedded Docs editor, do not start editing there by default; go to Feishu app -> 云文档/Docs, search the exact full document title, open the matching result, and continue only after the document is visible in the browser Docs host.
- If the target document is visible only in the Feishu desktop embedded Docs editor for a content/provision task, treat that as identity evidence but not as a valid editing host. Do not paste material, format text, insert structures, add comments, or return finished there; open/move the same target document to browser Docs first.
- If the task has no explicit target document title, do not invent one; use the current live browser Docs page when available, otherwise recover to a live Docs host before acting.
- If the requested document title is already visible in the Docs title, breadcrumb, or main document area, stay on that document and continue the requested operation. For entry/open/current-document tasks, return finished immediately instead of opening or searching for the same document again.
- If the requested target anchor, phrase, or paragraph is already visible in the current target document, operate directly on that visible target. Do not reopen document find/search, do not retype the same query, and do not use another host/window to search for something already visible.
- For entry/open tasks, readable target document visibility is enough; edit mode is required only for content, formatting, sharing, or permission changes.
- Unified entry protocol for document entry/open tasks:
  1. If the exact requested document title is visible in the current document title, breadcrumb, or main page title, return finished.
  2. If not, return to the Feishu app/Docs cloud-document entry surface: Feishu app -> 云文档/Docs. Do not use a browser Docs home as the default entry surface unless the case explicitly says the browser is the starting surface.
  3. Search the exact full requested document title from the Docs entry surface, using the cloud-docs content search box/top Docs search, not the far-left Feishu global search box or a recent-list shortcut.
  4. Open the matching result and then finish only after the exact title is visible on the document page.
- When switching from one already-open Docs document to a different named document, first return to the Feishu app/Docs cloud-document entry surface, then use the cloud-docs search box to search the exact title there. Do not open directly from the recent list as the default route, and do not use the editor-page top-right magnifier as the primary document-entry search.
- Prefer exact-title Docs search over browser-tab switching, recent-list guessing, sidebar guessing, or scanning many documents.
- If a Docs search box is already open and contains the exact full document title, visually identify and click the matching result with the exact title once. On the next screenshot, if the exact title is visible on the opened document page, return finished immediately. If the same search popup remains, do not click the same result again as the immediate next action; wait once for navigation/loading evidence, then use Enter or another visible open affordance only if the same focused result is still present.
- To close a Docs search popup, prefer Esc. The X inside a search input may only clear text or fail to dismiss the popup; if one close/X click leaves the popup unchanged, do not click that same X again.
- Recent documents and sidebar entries are not the default route for entry/open tasks. Use them only if the cloud-docs search surface is unavailable or broken after one clear attempt, and record that as fallback behavior.
- In Feishu Docs home/list/recent file tables, do not open a requested document directly from a recent row by default. Prefer the cloud-docs search box with the exact full title; use double-click on the exact title text only as fallback after search is unavailable or failed.
- For explicit new-document creation tasks, do not search for an existing same-title document first. If the exact requested document is not already open and already satisfying the goal, recover to Feishu app -> 云文档/Docs and use a visible New/Create document entry to create a fresh document with the requested title.
- For create-or-confirm/provisioning tasks that explicitly ask to confirm reuse of an existing target, first inspect whether the exact target cloud document is already open. If it is not, recover to Feishu app -> 云文档/Docs, search the exact full title at most once, and open the matching result or create it from that Feishu cloud-docs surface.
- Creation tasks must start from the Feishu app -> 云文档/Docs surface when the target document is not already open. Do not open a browser new tab, address bar, ordinary web page, browser history, or unrelated app to create the document.
- After opening or creating the provision target from Feishu cloud-docs, prefer the browser Docs host before typing the title/body material. Do not paste material into the Feishu desktop embedded editor when a browser Docs handoff can be reached.
- If a search popup shows no results for the exact full target title, close it with Esc or a visible close control before creating; do not retype the same query into the same popup.
- For provisioning after a no-result search, shortcut create entries such as an unlabeled `+` are allowed only with evidence gating. Use them when the surrounding UI, tooltip/menu, location in a Docs toolbar/sidebar, or previous visible state supports that it is a new/create control. If one shortcut attempt does not reveal a create/new-document menu or page, do not repeat it; switch to a clearer labeled `新建`, `新建文档`, `创建`, sidebar create entry, or Docs home create button.
- If provisioning is incomplete and the current surface is an existing document editor, first return to the cloud-docs home/library surface before using New/Create. Do not keep creating or repairing from inside an editor page.
- For new-document entry tasks, return finished as soon as a blank editable document page is visible with a title field or body editor. Do not set a title unless the instruction explicitly requests title input.
- Browser entry protocol: for browser-specific entry cases, if the current surface is a browser and a visible tab/page/sidebar/title contains Feishu Docs evidence such as `feishu.cn`, `larksuite.com`, `飞书云文档`, a Docs document title, or a Docs list/sidebar, use that visible Docs surface.
- For non-browser entry or target-document tasks, a frontmost browser Feishu Docs page is allowed as a precheck surface only. If it already shows the exact requested target document, use it or finish as appropriate. If it is Feishu Docs but not the target document, prefer switching/opening the Feishu app and entering 云文档/Docs, then use cloud-docs search with the full target title.
- A visible browser tab whose tab title clearly matches the exact requested target document may be used as a shortcut to activate that already-open target document. Do not use ordinary tab scanning as the primary entry strategy.
- If the browser has no visible Feishu Docs evidence, do not browse web pages, history, or unrelated tabs. Prefer switching/opening the Feishu app, entering 云文档/Docs, then searching the full target document title.

Avoid:
- Do not click browser tabs, address bars, app icons, or system menus while a usable Docs content area is visible, except for one visible exact-target document tab shortcut.
- Treat a depicted screenshot of a Docs page inside another app/page/report as a live editable Docs page.
- Use Docs keyboard shortcuts on a non-Docs surface just because the action target text says Feishu/Docs.
- Use browser tab switching as the primary way to move between documents during entry/open tasks.
- Do not perform content editing inside the Feishu desktop embedded Docs editor when the case names a target document and the browser Docs execution host can be reached through cloud-docs search.
- Do not use the far-left Feishu global search box as the primary search surface for cloud-document entry/open tasks.
- Do not open a requested cloud document from the recent list before trying the cloud-docs search box, unless search is unavailable or already failed.
- Do not use browser Docs home/search as the default entry route for non-browser entry cases.
- Do not use the editor-page top-right magnifier as the primary route for opening another named cloud document.
- Do not press Enter before clicking a visible exact-title search result.
- Do not reopen search with `command k` after the exact full document title is already typed into a visible Docs search field.
- Do not click the same exact-title search result in two consecutive steps.
- Do not click the same exact-title search result again after already clicking it, waiting, and pressing Enter on that same result.
- Do not operate controls depicted inside screenshots, images, cards, previews, or embedded content.
- Do not reopen the same search, menu, or dialog when the current visible state is already useful.
- Do not repeat click/click/double-click loops on the same visible document row/card just because the page has not changed yet.
- Do not open or click the same already opened target document again after the document title is visible.
- Do not repeat the same exact document-title search after a no-result state in a provisioning task.
- Do not repeat an ambiguous shortcut create button after it failed to reveal a create/new-document menu or page.
- Do not open unrelated apps such as WeChat, ordinary web search pages, browser history, bookmarks, or random tabs to find a document.

Batch:
- Batch only stable shell/navigation actions when every later target remains visible in the current screenshot.
