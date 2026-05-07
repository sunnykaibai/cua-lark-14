# Docs Share Permission

Use:
- For document sharing, open the visible Docs share/permission workflow, add or select the requested recipient, and confirm using visible dialog controls.
- If the recipient is already visible in the collaborator or permission list, treat that visible state as satisfied unless the task asks to change it.
- For inspect-only tasks, opening the relevant share/permission state is enough; do not send a new invitation.
- Chinese success messages such as 邀请成员成功, 已分享, 修改成员权限成功, or 已获得权限 are valid evidence.

Avoid:
- Copy a hidden link or paste a link into IM as a substitute for the Docs share workflow.
- Use backend state, DOM, local files, or hidden APIs to prove sharing.
- Add duplicate recipients when the permission state is already visible.

Batch:
- Do not batch across newly opened share dialogs, recipient pickers, or permission dropdowns.
