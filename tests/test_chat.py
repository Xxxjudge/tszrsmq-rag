import sys
sys.path.insert(0, '.')

from scripts.chat import build_prompt


def test_build_prompt_includes_context():
    docs = ["武则天是唐朝唯一的女皇帝。", "武则天在位期间重用寒门士人。"]
    question = "武则天为何重要？"
    prompt = build_prompt(docs, question)
    assert "武则天是唐朝唯一的女皇帝" in prompt
    assert "武则天在位期间重用寒门士人" in prompt
    assert "武则天为何重要" in prompt


def test_build_prompt_has_system_instruction():
    docs = ["任意内容"]
    prompt = build_prompt(docs, "任意问题")
    assert "唐史主任司马迁" in prompt


def test_build_prompt_includes_all_docs():
    docs = [f"内容片段{i}，关于唐朝历史的描述。" for i in range(5)]
    prompt = build_prompt(docs, "问题")
    for doc in docs:
        assert doc in prompt
