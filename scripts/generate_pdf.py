#!/usr/bin/env python3
"""
从 Markdown 知识库生成精美 PDF 备考文件。
支持多层级目录结构（知识点详解/、题型训练/ 等子目录）。
用法: python generate_pdf.py <input_dir> <output.pdf> [subject_name] [exam_date]
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# 尝试导入 PDF 生成库
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        Table, TableStyle, Image, ListFlowable, ListItem,
        KeepTogether, HRFlowable
    )
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


# ===== 颜色方案 =====
COLOR_PRIMARY = HexColor("#1a5276")      # 深蓝 — 标题
COLOR_SECONDARY = HexColor("#2980b9")    # 中蓝 — 二级标题
COLOR_ACCENT = HexColor("#e74c3c")       # 红色 — 重点标注
COLOR_ACCENT2 = HexColor("#f39c12")      # 橙色 — 次重点
COLOR_ACCENT3 = HexColor("#27ae60")      # 绿色 — 了解
COLOR_BG = HexColor("#f8f9fa")           # 浅灰背景
COLOR_BORDER = HexColor("#dee2e6")       # 边框


def register_fonts():
    """注册中文字体"""
    font_paths = [
        ("C:/Windows/Fonts/msyh.ttc", "Microsoft YaHei"),
        ("C:/Windows/Fonts/simsun.ttc", "SimSun"),
        ("C:/Windows/Fonts/simhei.ttf", "SimHei"),
        ("/System/Library/Fonts/PingFang.ttc", "PingFang"),
        ("/System/Library/Fonts/STHeiti Light.ttc", "STHeiti"),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "NotoSansCJK"),
    ]

    for fp, name in font_paths:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont("ChineseFont", fp))
                pdfmetrics.registerFont(TTFont("ChineseFontBold", fp))
                return True
            except Exception:
                continue

    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return True
    except Exception:
        pass

    return False


def create_styles():
    """创建 PDF 样式"""
    styles = getSampleStyleSheet()

    font_name = "ChineseFont" if _font_registered else "Helvetica"

    styles.add(ParagraphStyle(
        "CoverTitle", fontName=font_name, fontSize=28,
        leading=36, alignment=TA_CENTER, textColor=COLOR_PRIMARY,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        "CoverSubtitle", fontName=font_name, fontSize=14,
        leading=20, alignment=TA_CENTER, textColor=COLOR_SECONDARY
    ))
    styles.add(ParagraphStyle(
        "H1_CH", fontName=font_name, fontSize=20, leading=28,
        textColor=COLOR_PRIMARY, spaceBefore=24, spaceAfter=12,
        borderPadding=(0, 0, 2, 0)
    ))
    styles.add(ParagraphStyle(
        "H2_CH", fontName=font_name, fontSize=16, leading=22,
        textColor=COLOR_SECONDARY, spaceBefore=16, spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        "H3_CH", fontName=font_name, fontSize=13, leading=18,
        textColor=COLOR_PRIMARY, spaceBefore=12, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        "Body_CH", fontName=font_name, fontSize=10, leading=16,
        alignment=TA_JUSTIFY, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        "KeyPoint", fontName=font_name, fontSize=11, leading=16,
        textColor=COLOR_ACCENT, spaceAfter=6, leftIndent=10
    ))
    styles.add(ParagraphStyle(
        "TableHeader", fontName=font_name, fontSize=10, leading=14,
        textColor=white, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        "TableCell", fontName=font_name, fontSize=9, leading=13
    ))
    styles.add(ParagraphStyle(
        "Footer", fontName=font_name, fontSize=8, leading=10,
        textColor=HexColor("#999999"), alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        "SectionTitle", fontName=font_name, fontSize=22, leading=30,
        textColor=COLOR_PRIMARY, alignment=TA_CENTER,
        spaceBefore=10, spaceAfter=20, borderPadding=(0, 0, 4, 0)
    ))

    return styles


def build_header_footer(canvas, doc):
    """页眉页脚"""
    canvas.saveState()
    canvas.setStrokeColor(COLOR_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(20*mm, A4[1] - 15*mm, A4[0] - 20*mm, A4[1] - 15*mm)
    canvas.setFont("ChineseFont" if _font_registered else "Helvetica", 8)
    canvas.setFillColor(HexColor("#999999"))
    canvas.drawCentredString(A4[0]/2, 15*mm, f"— {canvas.getPageNumber()} —")
    canvas.restoreState()


def parse_md_to_pdf_elements(md_text: str, styles) -> list:
    """将 Markdown 文本解析为 PDF 元素列表"""
    elements = []
    lines = md_text.split("\n")
    styles_dict = styles
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # 代码块
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            if not in_code_block:
                elements.append(Spacer(1, 2*mm))
            continue

        if in_code_block:
            elements.append(Paragraph(f"<font face='Courier' size='8'>{stripped}</font>", styles_dict["Body_CH"]))
            continue

        if not stripped:
            elements.append(Spacer(1, 4*mm))
            continue

        # 标题
        if stripped.startswith("# ") and not stripped.startswith("## "):
            elements.append(Paragraph(stripped[2:], styles_dict["H1_CH"]))
            elements.append(HRFlowable(width="100%", thickness=1, color=COLOR_BORDER))
        elif stripped.startswith("## "):
            elements.append(Paragraph(stripped[3:], styles_dict["H2_CH"]))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER, spaceAfter=4))
        elif stripped.startswith("### "):
            elements.append(Paragraph(stripped[4:], styles_dict["H3_CH"]))
        elif stripped.startswith("#### "):
            elements.append(Paragraph(f"<b>{stripped[5:]}</b>", styles_dict["Body_CH"]))
        # 重点行
        elif "★" in stripped or "【老师重点" in stripped or "必考" in stripped:
            elements.append(Paragraph(stripped, styles_dict["KeyPoint"]))
        # 分割线
        elif stripped == "---":
            elements.append(Spacer(1, 4*mm))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER))
            elements.append(Spacer(1, 4*mm))
        # 一级表格行
        elif stripped.startswith("|"):
            continue  # 跳过行内表格，简单处理
        # 列表项
        elif stripped.startswith("- ") or stripped.startswith("* "):
            text = stripped[2:]
            if "★" in text:
                elements.append(Paragraph(f"• {text}", styles_dict["KeyPoint"]))
            else:
                elements.append(Paragraph(f"• {text}", styles_dict["Body_CH"]))
        elif stripped.startswith("> "):
            text = stripped[2:]
            elements.append(Paragraph(f"<i>{text}</i>", styles_dict["Body_CH"]))
        # 视频链接
        elif "[▽视频推荐]" in stripped or "[视频]" in stripped:
            elements.append(Paragraph(stripped, styles_dict["Body_CH"]))
        # 普通文本
        else:
            text = stripped.replace("**", "<b>").replace("__", "<b>")
            while text.count("<b>") > text.count("</b>"):
                text += "</b>"
            elements.append(Paragraph(text, styles_dict["Body_CH"]))

    return elements


def collect_all_files(input_dir: str) -> list:
    """收集所有 Markdown 文件，按正确顺序排列"""
    base = Path(input_dir)
    ordered_files = []

    # 定义顶层文件读取顺序
    top_level_order = [
        "00_学习方案",
        "01_考试重点总览",
        "02_知识体系图谱",
    ]

    for prefix in top_level_order:
        for f in sorted(base.glob(f"{prefix}*.md")):
            ordered_files.append(("top", f))

    # 知识点详解
    knowledge_dir = base / "03_知识点详解"
    if knowledge_dir.exists():
        ordered_files.append(("section", None))  # 标记新 section
        for f in sorted(knowledge_dir.glob("*.md")):
            ordered_files.append(("knowledge", f))

    # 题型训练
    training_dir = base / "04_题型训练"
    if training_dir.exists():
        ordered_files.append(("section", None))
        # 按题型顺序
        training_order = ["选择题训练", "填空题训练", "简答题背诵版", "计算题训练", "综合题训练"]
        for prefix in training_order:
            for f in sorted(training_dir.glob(f"{prefix}*.md")):
                ordered_files.append(("training", f))
        # 其他未匹配的
        for f in sorted(training_dir.glob("*.md")):
            if not any(f.stem.startswith(p) for p in training_order):
                ordered_files.append(("training", f))

    # 模拟卷
    for f in sorted(base.glob("05_模拟试卷*.md")):
        ordered_files.append(("top", f))

    # 视频
    for f in sorted(base.glob("06_速成视频合集*.md")):
        ordered_files.append(("top", f))

    # 公式速查
    for f in sorted(base.glob("07_核心公式速查*.md")):
        ordered_files.append(("top", f))

    # 兜底：任何遗漏的顶层文件
    known_stems = set()
    for _, f in ordered_files:
        if f:
            known_stems.add(f.stem)
    for f in sorted(base.glob("*.md")):
        if f.stem not in known_stems:
            ordered_files.append(("top", f))

    return ordered_files


def generate_pdf(input_dir: str, output_path: str, subject: str, exam_date: str):
    """主函数：生成 PDF"""
    if not HAS_REPORTLAB:
        print("reportlab 未安装。请运行: pip install reportlab")
        sys.exit(1)

    global _font_registered
    _font_registered = register_fonts()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
        title=f"{subject}备考资料",
        author="exam-prep-assistant"
    )

    styles = create_styles()
    elements = []

    # ===== 封面 =====
    elements.append(Spacer(1, 40*mm))
    elements.append(Paragraph(subject, styles["CoverTitle"]))
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph("考试备考资料", styles["CoverSubtitle"]))
    elements.append(Spacer(1, 6*mm))
    if exam_date:
        elements.append(Paragraph(f"考试时间: {exam_date}", styles["CoverSubtitle"]))
    elements.append(Paragraph(f"生成日期: {datetime.now().strftime('%Y年%m月%d日')}", styles["CoverSubtitle"]))
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph("本资料由 AI 智能备考助手自动生成", styles["Footer"]))
    elements.append(PageBreak())

    # ===== 读取所有 MD 文件 =====
    ordered_files = collect_all_files(input_dir)

    section_titles = {
        "knowledge": "知识点详解",
        "training": "题型训练",
    }

    for file_type, md_file in ordered_files:
        if file_type == "section":
            # 不额外加 section 标记，子文件自带头部标题
            continue

        if md_file is None:
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # 生成可读的章节名
        stem = md_file.stem
        # 去掉数字前缀 (如 00_、01_、第三章_)
        chapter_name = stem
        # 保留原文件名作为标题
        elements.append(Paragraph(chapter_name.replace("_", " ").replace("-", " "), styles["H1_CH"]))
        elements.append(HRFlowable(width="100%", thickness=1, color=COLOR_PRIMARY))
        elements.append(Spacer(1, 6*mm))

        elements.extend(parse_md_to_pdf_elements(content, styles))
        elements.append(PageBreak())

    # 生成 PDF
    doc.build(elements, onFirstPage=build_header_footer, onLaterPages=build_header_footer)
    print(f"PDF 已生成: {output_path}")


def main():
    if not HAS_REPORTLAB:
        print("=" * 50)
        print("【!!注意!!】 reportlab 未安装，无法直接生成 PDF。")
        print("    请运行: pip install reportlab")
        print("    然后重新执行此脚本。")
        print("=" * 50)
        print()
        print("替代方案：将 Markdown 知识库通过浏览器打印为 PDF。")
        print("   1. 用 VS Code 打开知识库目录")
        print("   2. 安装 Markdown PDF 扩展")
        print("   3. 右键 → Markdown PDF: Export (pdf)")
        sys.exit(1)

    if len(sys.argv) < 3:
        print("用法: python generate_pdf.py <input_dir> <output.pdf> [subject_name] [exam_date]")
        print("示例: python generate_pdf.py ./高数备考知识库 ./高数备考资料.pdf 高等数学 2026-07-15")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_path = sys.argv[2]
    subject = sys.argv[3] if len(sys.argv) > 3 else Path(input_dir).parent.name
    exam_date = sys.argv[4] if len(sys.argv) > 4 else ""

    if not Path(input_dir).exists():
        print(f"错误: 输入目录不存在 — {input_dir}")
        sys.exit(1)

    generate_pdf(input_dir, output_path, subject, exam_date)


if __name__ == "__main__":
    main()
