#!/usr/bin/env python3
"""Сборка офлайн-демо: template.html + контент из backend/content/*.json → index.html."""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(HERE, "..", "backend", "content")
TEMPLATE = os.path.join(HERE, "template.html")
OUT = os.path.join(HERE, "index.html")


def main():
    payloads = []
    for f in sorted(glob.glob(os.path.join(CONTENT_DIR, "*.json"))):
        with open(f, encoding="utf-8") as fh:
            payloads.append(json.load(fh))

    data_js = json.dumps(payloads, ensure_ascii=False, separators=(",", ":"))
    # защита от преждевременного закрытия <script>
    data_js = data_js.replace("</", "<\\/")

    with open(TEMPLATE, encoding="utf-8") as fh:
        html = fh.read()
    html = html.replace("__BILIM_DATA__", data_js)

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)

    n_topics = sum(len(t.get("topics", []))
                   for p in payloads for t in p.get("sections", []))
    n_q = sum(len(t.get("questions", []))
              for p in payloads for s in p.get("sections", []) for t in s.get("topics", []))
    print(f"OK: {OUT}")
    print(f"предметов: {len(payloads)}, тем: {n_topics}, вопросов: {n_q}, "
          f"размер: {os.path.getsize(OUT) // 1024} KB")


if __name__ == "__main__":
    main()
