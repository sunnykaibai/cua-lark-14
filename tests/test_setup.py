from cua_lark.domain.models import TestCase
from cua_lark.testing.setup import build_setup_step_prompt


def test_setup_prompt_for_entry003_uses_fixed_decoy_recipe():
    case = TestCase(
        id="DOCS-ENTRY-003-SETUP",
        name="从非目标文档切换到指定文档 setup",
        instruction="前提：目标文档“CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET”和非目标夹具文档“CUA-Lark Docs 入口鲁棒性非目标文档 DOCS-ENTRY-DECOY”都已经存在。",
        expected="当前界面打开名为“CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET”的云文档",
        stage="docs_entry_robustness_setup",
        setup_instruction="前提：目标文档“CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET”和非目标夹具文档“CUA-Lark Docs 入口鲁棒性非目标文档 DOCS-ENTRY-DECOY”都已经存在。",
        setup_expected="当前打开的是已有的“CUA-Lark Docs 入口鲁棒性非目标文档 DOCS-ENTRY-DECOY”云文档编辑页，而不是目标文档；过程中没有新建空白文档。",
    )

    prompt = build_setup_step_prompt(case, [])

    assert "Setup mode protocol:" in prompt
    assert "framework-controlled setup" in prompt
    assert "CUA-Lark Docs 入口鲁棒性非目标文档 DOCS-ENTRY-DECOY" in prompt
    assert "Do not create a new document and do not leave the setup on the target document." in prompt
    assert "search the exact full decoy title once" in prompt


def test_setup_prompt_for_entry004_stays_browser_only():
    case = TestCase(
        id="DOCS-ENTRY-004-SETUP",
        name="从浏览器 Docs 页面打开指定文档 setup",
        instruction="在当前浏览器里的飞书云文档首页、最近文档页或搜索页中，打开“CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET”",
        expected="当前浏览器飞书 Docs 页面显示“CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET”",
        stage="docs_entry_robustness_setup",
        setup_instruction="前提：目标文档“CUA-Lark Docs 入口鲁棒性测试文档 DOCS-ENTRY-TARGET”已经存在。请切到浏览器承载的飞书云文档首页、最近文档页或搜索页，不要停留在任何文档编辑页。",
        setup_expected="当前可见界面是浏览器中的飞书云文档首页、最近文档页或搜索页，主内容区不是目标文档编辑页。",
    )

    prompt = build_setup_step_prompt(case, [])

    assert "browser-hosted Feishu Docs home" in prompt
    assert "Do not switch this setup to the desktop Feishu app." in prompt
    assert "browser Docs route only" in prompt


def test_setup_prompt_uses_setup_case_expected_and_blocks_system_ui():
    case = TestCase(
        id="DOCS-ENTRY-001-SETUP",
        name="从飞书当前界面打开指定文档 setup",
        instruction="离开目标文档，回到飞书云文档首页或消息页",
        expected="当前界面是飞书或飞书云文档的非目标文档编辑页，目标文档已经存在但没有打开在主内容区。",
        stage="docs_entry_robustness_setup",
    )

    prompt = build_setup_step_prompt(case, [])

    assert "当前界面是飞书或飞书云文档的非目标文档编辑页" in prompt
    assert "Do not use the macOS menu bar" in prompt
    assert "window menus" in prompt
