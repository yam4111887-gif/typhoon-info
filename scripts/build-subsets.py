#!/usr/bin/env python3
"""Build self-hosted font subsets for typhoon-info（比照 game-radar v4 SOP）.

Outputs into typhoon-info/fonts/:
  - NotoSansTC-sub.woff2   (variable wght 100-900; charset = 全站語系語料 + Big5 常用字 + 越南文 + 假名 + 標點塊)
  - ChakraPetch-{Medium,SemiBold,Bold}.woff2 (Latin + Latin-ext + Vietnamese + 符號)
  - OFL 授權條款二份

語料來源：index.html / privacy.html / disclaimer.html / {vi,en,ja}/index.html
（zh-Hant + 日本語 + Tiếng Việt + English 四語全系）。
執行：python3 scripts/build-subsets.py（需 /tmp/fonts 來源 TTF 與 fontTools）。
"""
import glob
import os
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "/tmp/fonts"
OUT = os.path.join(REPO, "fonts")
os.makedirs(OUT, exist_ok=True)

# ---------- 1. 語料 charset ----------
corpus_chars = set()
for pattern in ("*.html", "*/index.html"):
    for path in glob.glob(os.path.join(REPO, pattern)):
        with open(path, encoding="utf-8", errors="ignore") as f:
            corpus_chars.update(f.read())

# ASCII printable
corpus_chars.update(chr(c) for c in range(0x20, 0x7F))
# Latin-1 letters（含變音）、Latin Ext A/B（ă ơ ư Đ…）、Latin Ext Additional（越南文整塊）
for start, end in (
    (0x00C0, 0x00FF),
    (0x0100, 0x017F),
    (0x0180, 0x024F),
    (0x1E00, 0x1EFF),
):
    corpus_chars.update(chr(c) for c in range(start, end + 1))
# CJK 標點、假名（平/片 + 小型補充）、全形形式、常用箭頭、破折號/引號/刪節號等
for start, end in (
    (0x3000, 0x303F),  # CJK punctuation
    (0x3041, 0x30FF),  # 平假名 + 片假名
    (0x31F0, 0x31FF),  # 假名小型補充
    (0xFF01, 0xFF60),  # 全形形式
    (0x2190, 0x2199),  # 常用箭頭
    (0x2013, 0x2014),  # – —
    (0x2018, 0x201D),  # ‘ ’ “ ”
    (0x2022, 0x2026),  # • …
    (0x00B7, 0x00B7),  # ·
    (0x00A9, 0x00A9),  # ©
    (0x00D7, 0x00D7),  # ×
    (0x00B0, 0x00B0),  # °
):
    corpus_chars.update(chr(c) for c in range(start, end + 1))

# Big5 level-1（常用字，未來內容更新保險）→ unicode via big5 codec
big5 = set()
for hi in range(0xA4, 0xC7):
    for lo in list(range(0x40, 0x7F)) + list(range(0xA1, 0xFF)):
        if (hi, lo) > (0xC6, 0x7E):
            break
        try:
            ch = bytes([hi, lo]).decode("big5")
            if len(ch) == 1:
                big5.add(ch)
        except UnicodeDecodeError:
            pass

charset = corpus_chars | big5
print(f"corpus unique: {len(corpus_chars)} | big5 L1: {len(big5)} | union: {len(charset)}")

text_file = os.path.join(SRC, "charset.txt")
with open(text_file, "w", encoding="utf-8") as f:
    f.write("".join(sorted(charset)))

# ---------- 2. subset Noto variable ----------
noto_out = os.path.join(OUT, "NotoSansTC-sub.woff2")
subprocess.run(
    [
        "python3", "-m", "fontTools.subset", os.path.join(SRC, "NotoSansTC-var.ttf"),
        f"--text-file={text_file}",
        f"--output-file={noto_out}",
        "--flavor=woff2",
        "--layout-features=*",
        "--name-IDs=*",
        "--drop-tables+=DSIG",
    ],
    check=True,
)
axes = subprocess.run(
    ["python3", "-c",
     "from fontTools.ttLib import TTFont;f=TTFont(r'%s');print([(a.axisTag,a.minValue,a.maxValue) for a in f['fvar'].axes])" % noto_out],
    capture_output=True, text=True)
print("noto axes:", axes.stdout.strip())
print("noto size:", round(os.path.getsize(noto_out) / 1024), "KB")

# ---------- 3. subset Chakra Petch（Latin + Latin-ext + 越南文 + 符號）----------
chakra_text = "".join(sorted(
    {chr(c) for c in range(0x20, 0x7F)}
    | {chr(c) for c in range(0xC0, 0x250)}     # Latin-1 + Ext-A/B（含 Ă Ơ Ư Đ）
    | {chr(c) for c in range(0x1E00, 0x1F00)}   # 越南文擴充
    | set("·—–…‘’“”→←↑↓↔©°±×¥€£")
))
chakra_file = os.path.join(SRC, "chakra-charset.txt")
with open(chakra_file, "w", encoding="utf-8") as f:
    f.write(chakra_text)

for weight in ("Medium", "SemiBold", "Bold"):
    out = os.path.join(OUT, f"ChakraPetch-{weight}.woff2")
    subprocess.run(
        [
            "python3", "-m", "fontTools.subset", os.path.join(SRC, f"ChakraPetch-{weight}.ttf"),
            f"--text-file={chakra_file}",
            f"--output-file={out}",
            "--flavor=woff2",
            "--layout-features=*",
            "--name-IDs=*",
        ],
        check=True,
    )
    print(f"chakra {weight}:", round(os.path.getsize(out) / 1024), "KB")

# ---------- 4. OFL 授權條款 ----------
for src_name, dst_name in (("ofl-noto.txt", "OFL-NotoSansTC.txt"), ("ofl-chakra.txt", "OFL-ChakraPetch.txt")):
    src = os.path.join(SRC, src_name)
    if os.path.exists(src):
        with open(src, encoding="utf-8") as f:
            data = f.read()
        with open(os.path.join(OUT, dst_name), "w", encoding="utf-8") as f:
            f.write(data)
        print(f"license: {dst_name}")

print("DONE")
