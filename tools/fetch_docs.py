# -*- coding: utf-8 -*-
"""Exynos AI Studio SDK 3.0 문서를 사이트 공개 API 에서 내려받아 sdk_docs/raw/ 에 저장한다.

사이트는 React SPA 라 HTML 에 본문이 없다. 문서 뷰어가 부르는 API 를 그대로 쓴다.
  · 메뉴 트리 : GET /api/v1/document?search=ai-studio-document.json&categoryUrl=ai-studio
  · 본문      : GET /api/v1/document?search=ai-studio-<메뉴 name>&categoryUrl=ai-studio
                (파일명이 아니라 메뉴에 보이는 이름으로 찾는다)
서버가 가끔 엉뚱한 오류를 돌려주므로 success 가 올 때까지 몇 번 다시 시도한다.

    python tools/fetch_docs.py
"""

import json
import os
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "sdk_docs", "raw")
API = "https://soc-developer.semiconductor.samsung.com/api/v1/document"
PAGE = "https://soc-developer.semiconductor.samsung.com/global/development/ai-studio/document/"
SECTION_PREFIX = "SDK 3.0"


def get(search):
    q = urllib.parse.urlencode({"search": search, "categoryUrl": "ai-studio"})
    last = None
    for _ in range(8):
        req = urllib.request.Request(API + "?" + q, headers={"User-Agent": "Mozilla/5.0",
                                                             "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            last = json.loads(resp.read().decode("utf-8"))
        if last.get("success"):
            return last["data"]["documentDescription"]
        time.sleep(1.5)
    raise RuntimeError("문서를 받지 못했습니다: %s (%s)" % (search, (last or {}).get("msg")))


def main():
    os.makedirs(OUT, exist_ok=True)
    menu = json.loads(get("ai-studio-document.json"))
    items = [s for top in menu if top["name"].startswith(SECTION_PREFIX) for s in top.get("submenu") or []]
    index = []
    for it in items:
        body = get("ai-studio-" + it["name"])
        lang = "ko" if "/korean/" in it["fileName"] else "en"
        name = "%s_%s" % (lang, it["fileName"].split("/")[-1])
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(body)
        index.append({"title": it["name"], "slug": it["slug"], "lang": lang, "file": name,
                      "chars": len(body), "url": PAGE + it["slug"]})
        print("저장:", name, len(body))
    with open(os.path.join(ROOT, "sdk_docs", "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print("문서 %d개" % len(index))


if __name__ == "__main__":
    main()
