# study400question

《400 Questions Guide for Investment Banking Interviews: 2025 Edition》(BIWS) 的个人学习网页。

- `app/index.html`：学习台网页（知识树、中英对照、划词翻译、问 Claude、笔记、间隔重复复习、Story Bank），发布为私有的 claude.ai Artifact。
- `tools/parse_book.py`：把 PDF 解析成「部分 → 小节 → 题目」结构的 JSON。
- `tools/build_content.py`：加上中文标题、校验中文译文与英文逐段对齐，输出 `app/content/book.json`。

书的正文和译文（`app/content/`）属于版权内容，不提交到仓库。重新生成：

```
pip install pymupdf
python3 tools/parse_book.py 400-Questions-IB-Interview-Guide-2025.pdf /tmp/parsed.json
python3 tools/build_content.py /tmp/parsed.json
```
