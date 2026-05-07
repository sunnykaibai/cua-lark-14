# Docs Structure

Use:
- Create headings, lists, task lists, quote blocks, code blocks, tables, and dividers through visible formatting controls, slash commands, editor shortcuts known from visible UI, or editor markdown that visibly renders correctly.
- For table tasks, prefer a visible table insert control, toolbar/menu table control, or slash-menu table option. A plain Markdown table that remains as literal text is not a rendered table and is not success.
- Before using a slash command for any structure insertion, first close find/search popups, floating toolbars, slash remnants, insert menus, and editing-mode menus; then confirm focus is in a true empty body block at the target anchor, with the caret at the start of that empty block.
- After clicking the trailing end of an anchor line or a body insertion point once, treat the caret as likely placed even if it is hard to see. Do not repeatedly click the same line end. The next step must create the empty block with Enter/Shift Enter, open a visible insert/table control, paste/move content, or use another clear fallback.
- Press a real slash key with `hotkey(key='/')` and wait for a visible slash menu before typing any keyword. Do not use `type_text('/')` for the slash trigger because pasted slash text may stay as ordinary body text.
- If the top-right editing-mode dropdown (`编辑` / `修订` / `阅读`) is open, close or settle it before pressing slash. Slash commands should be triggered from body focus, not while a mode dropdown, floating toolbar, insert menu, or other transient UI has focus.
- Slash command success is visual: a slash menu, command search field, or block menu must appear. If `/` simply remains as a document character, the trigger failed.
- Do not type `表格` after `/` unless the slash menu or slash-command search field is visibly open and receiving the keyword. If `/` appears as ordinary body text, immediately clear that literal `/`; do not continue with a keyword.
- Try slash once per insertion attempt. After one failed literal `/`, do not keep typing slash keywords; clean the residue and use a visible toolbar, block-type, insert, table, list, or divider control path.
- Do not use the top-right global `+` / new-create menu for inline document tables. Items such as `多维表格`, `表格`, `文档`, or app templates create separate objects rather than an inline table at the anchor.
- If a plain Markdown table such as `| 事项 | 负责人 | 状态 |` remains visible after insertion, do not repeatedly press Enter to force conversion. Use a visible table control or insert a real rendered table nearby and fill the requested cells.
- Once a rendered table grid is visible, fill cells in reading order: header row left-to-right, then data rows left-to-right.
- Do not press Enter to move between table cells. Enter may add a line inside the current cell; click the next visible empty cell before typing the next value.
- Before typing into a table cell, check whether the intended header or value is already visible in that same cell. Do not duplicate a cell value.
- Headers and data values must be in separate table rows with a visible horizontal row boundary between them. Text stacked as two lines inside the same cell is not a valid two-row table.
- Reject the common bad pattern where `事项` is directly above `素材复核`, `负责人` directly above `测试扩展`, and `状态` directly above `完成` inside the same three tall cells with no horizontal grid line between header and data. An empty row below does not count as the filled data row.
- If a dirty run left headers and data stacked inside the same cells with an empty row below, repair before finishing: move the data values into the empty row cells, or replace the bad table with one clean table whose header and data rows are visibly separated.
- Table row separation geometry check (MANDATORY before finishing): a correctly separated 2-row table has SHORT cells (one line per cell). If the first-row cells are TALL (roughly double height) and each shows two lines stacked vertically (header text above data text within the same cell), the table has the stacking defect. You MUST repair it: click into each cell of the empty second row and type the data value there, then delete the data text from the first-row cells.
- Visual cue: count horizontal grid lines between text-containing rows. A valid header+data table has at least one full-width grid line between the header text and data text. If '事项' and '素材复核' are separated only by a line break (no full-width grid line between them), the table is broken.
- For divider tasks, a typed `/分割线` or `/divider` string is only a trigger, not success. If plain text remains after the trigger, delete it and use the visible divider insertion control or slash-menu option until a rendered horizontal divider is visible.
- For divider tasks, do not batch the anchor/insertion click together with typing `---`. First focus the exact point between the anchors, inspect the next screenshot, then insert the divider only if the caret/location is correct.
- For divider tasks, do not loop inside insert/slash menus. If a divider/separator option is not visible after one scroll or one clear menu attempt, close the menu, focus the empty body block between the target paragraphs, type `---`, and press Enter once as a Markdown divider shortcut.
- After typing `---` and pressing Enter once for a divider task, do not type `---` again on the next step. First inspect for a thin rendered gray divider; that line is easy to miss but counts as the divider.
- If `---` remains as plain body text after Enter, delete only that trigger text and switch to a clearly visible insert/separator control. Do not keep typing slash keywords or repeatedly click `更多`.
- For divider tasks between two existing paragraphs/anchors, avoid leaving an extra blank editable paragraph between the rendered divider and the after-anchor. The after-anchor should visually follow the divider with only normal editor spacing, not a separate empty body line.
- For divider tasks, finish as soon as a rendered horizontal divider is visibly between the requested before/after anchors and there is no obvious extra blank paragraph inserted below it. A thin gray horizontal line is valid divider evidence even if a find box, red search highlight, or caret is still visible; do not click the divider area again just to confirm it.
- For heading plus outline tasks, create the heading first, then use the visible document outline/目录 control or document outline sidebar to locate it.
- Distinguish the document outline/目录 from the global Feishu file/navigation sidebar. The global sidebar contains items like 主页, 云盘, 知识库, recent documents, or document library entries; scrolling or clicking that sidebar does not satisfy a TOC navigation task.
- After creating the requested heading, do not scroll the global file/navigation sidebar to look for the heading. Open the document's own 目录/outline panel, then click the exact heading entry there once. If the new heading is already visible in the document body and the TOC step is not required, finish immediately.
- For maintenance tasks that remove a Markdown marker before an existing rendered heading, finish immediately if the target heading text is already visible without the marker and still appears as a heading. Do not click before the heading or press Backspace just because the instruction mentions the old marker form.
- For marker-cleanup maintenance, do not switch view/edit mode just to hunt for an old `#` marker when the current screenshot already shows the target heading rendered without `#`.
- Only edit marker-cleanup headings when a visible leading `#` or `# ` is directly before the target heading text.
- If a marker-removal attempt merges the target heading into the previous paragraph/list item or removes the heading style, use undo once and reassess before any further edit.
- For checklist tasks, keep the requested open item unchecked and mark only the requested done item checked.
- For checklist/task-list tasks, do not choose divider/separator/分割线 menu items, and do not accept a rendered horizontal line as progress. A divider is wrong output for a checklist task.
- Prefer visible options named 待办, 任务, 任务列表, checklist, or checkbox. If the visible menu row says 分割线/divider/separator, skip it and keep looking for the checklist/task-list option or use another visible checklist control.
- If a divider appears where checklist items should be, treat it as a wrong structure and repair before finishing by creating the two requested checklist items after the divider or undoing the divider if safe.
- For nested lists, parent and child text must both be visible with the child indented under the parent.

Avoid:
- Treat plain labels, markdown markers, Markdown table text, or ordinary numbered text as structured content when the task requires rendered structure.
- Leave literal trigger text such as `/`, `/表格`, `/分割线`, or Markdown pipe-table text in the body and still finish.
- Treat header/data text stacked inside the same table cells as a valid table with separate rows.
- Repeatedly type markers after the requested structured content is already visible.
- Repeatedly click the same anchor line end or insertion point after it was already clicked once for a structure insertion.
- Treat table cells as table-fill targets, not anchor insertion points. Do not block or replace a deliberate click into a header/data cell with an Enter key.
- Re-click a newly inserted divider or its surrounding empty line after the divider is already visible between the requested anchors.
- Leave an obvious extra blank editable paragraph below a newly inserted divider when the task only asked to separate two existing anchors.
- Treat a horizontal divider as success for a checklist/task-list/todo task.
- Scroll or click the global Feishu file/navigation sidebar when the task asks to use the document 目录/outline.
- Repeatedly press Backspace before a heading when no visible marker remains.
- Invent unverified shortcuts when a visible style or block-type control is available.

Batch:
- Do not batch across newly opened slash menus, block-type menus, table pickers, or checklist conversion controls.
