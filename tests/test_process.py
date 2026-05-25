import sys
sys.path.insert(0, '.')

from scripts.process import clean_text, chunk_post, prepare_chunks


def test_clean_removes_html_tags():
    raw = '<a href="/u/123">@某人</a> 这是正文内容，讲述唐朝历史。'
    result = clean_text(raw)
    assert '<' not in result
    assert '这是正文内容' in result


def test_clean_removes_topic_tags():
    raw = '#唐朝历史# 李世民即位后开创贞观之治。'
    result = clean_text(raw)
    assert '#' not in result
    assert '李世民即位后' in result


def test_clean_removes_urls():
    raw = '详见 http://t.cn/abc123 这篇文章分析了安史之乱。'
    result = clean_text(raw)
    assert 'http' not in result
    assert '这篇文章分析了安史之乱' in result


def test_clean_strips_whitespace():
    raw = '  武则天   称帝  '
    result = clean_text(raw)
    assert result == '武则天 称帝'


def test_chunk_short_post_returns_single_chunk():
    text = '贞观之治是唐太宗李世民在位期间出现的政治清明、经济恢复、文化繁荣的局面。'
    chunks = chunk_post(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_long_post_splits_by_length():
    text = '唐朝历史' * 130  # 520 字
    chunks = chunk_post(text, max_len=500, overlap=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 500


def test_chunk_overlap():
    text = 'A' * 450 + 'B' * 450  # 900 字
    chunks = chunk_post(text, max_len=500, overlap=50)
    assert len(chunks) == 2
    assert chunks[1][:50] == 'A' * 50


def test_prepare_chunks_filters_reposts():
    posts = [
        {"id": "1", "text": "原创内容" * 20, "created_at": "2024-01-01", "is_repost": False},
        {"id": "2", "text": "转发内容" * 20, "created_at": "2024-01-02", "is_repost": True},
    ]
    chunks = prepare_chunks(posts)
    assert all(c["post_id"] == "1" for c in chunks)


def test_prepare_chunks_filters_short_posts():
    posts = [
        {"id": "1", "text": "短", "created_at": "2024-01-01", "is_repost": False},
        {"id": "2", "text": "这是一篇足够长的微博内容，详细讲述了唐朝的历史背景和社会制度。" * 3,
         "created_at": "2024-01-02", "is_repost": False},
    ]
    chunks = prepare_chunks(posts)
    assert all(c["post_id"] == "2" for c in chunks)


def test_prepare_chunks_assigns_unique_ids():
    long_text = "唐朝历史" * 130  # 520 字，会被分成多块
    posts = [{"id": "99", "text": long_text, "created_at": "2024-01-01", "is_repost": False}]
    chunks = prepare_chunks(posts)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))
