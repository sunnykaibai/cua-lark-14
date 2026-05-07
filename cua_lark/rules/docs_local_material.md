# Docs Local Material

Use:
- Local Markdown or text material in the prompt is content to paste/type after the correct visible Docs editor area is focused.
- Use the provided material reference token in Action content when the material is long.
- For bounded snippets, paste/type the requested snippet once after the requested anchor.
- For agenda snippets, ensure both required bullets such as 同步目标 and 确认风险 are visible before finishing.
- The pasted result must be at the requested target anchor. Do not count the original material/source section elsewhere in the same document as task completion.
- Do not paste START/END boundary markers unless the instruction explicitly asks for them.
- If an earlier wrong paste and a later correct paste are both visible, clean the wrong version before finishing.
- Markdown paste is not guaranteed to render in Feishu Docs. After pasting Markdown content for a clean Docs result, inspect the visible result before finishing.
- If a heading line remains as raw Markdown such as `# Title` or `### Title`, treat that as an unrendered paste. Repair by removing only the leading marker and following space, preserving the title text, then use a visible paragraph-style/block-type/slash menu control to convert the line to the requested heading style.
- If list lines remain as raw Markdown such as `- 同步目标`, repair by removing only the literal `- ` prefixes or selecting the lines, then use a visible bullet-list/list control to convert them into real list items.
- If a Markdown pipe table remains as literal text, do not try to fix it by deleting pipe characters. Insert a real Docs table/grid or table-like block near the target anchor and fill the cells with the Markdown table's header and row values.
- After a Markdown self-repair, verify that the target result no longer contains raw Markdown markers, START/END markers, full-material roots, or duplicate wrong versions near the target anchor.

Avoid:
- Treat the local file path or prompt material itself as proof that the GUI task is complete.
- Paste the same snippet again after the snippet heading and requested bullet lines are already visible.
- Paste the whole material file when the task asks for a bounded snippet.
- Leave raw Markdown trigger syntax such as `###`, literal `- ` bullets, pipe tables, or isolated punctuation when the task expects a clean Docs result.
- Delete title/list content while trying to remove Markdown markers; remove only the marker characters and preserve the requested text.
- Keep retrying the same raw Markdown paste after seeing that Feishu did not render it.
- Use local files, DOM, APIs, or hidden links to bypass visible Docs operation.

Batch:
- Batch body focus plus material paste only when the target insertion point is visible and stable.
