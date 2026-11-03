"""Tạo PDF mẫu tiếng Anh (nội dung tự viết, CC0) để thử và đo chất lượng dịch.

Bố cục cố ý đa dạng: trang bìa, 2 cột, danh sách, bảng, biểu đồ ảnh, hộp tô nền, chú thích chân trang, liên kết.
    python tao_pdf_mau.py --pages 6 --out mau_6trang.pdf      (6 trang mẫu)
    python tao_pdf_mau.py --pages 60 --out mau_60trang.pdf    (lặp mẫu để thử tài liệu dài)
    python tao_pdf_mau.py --pages 150 --out mau_150trang.pdf  (thử giới hạn lượt dùng)
"""
import argparse
import io

import pymupdf

W, H = 612, 792
CSS = """
body { font-family: serif; font-size: 10.5pt; color: #222; }
h1 { font-family: sans-serif; font-size: 20pt; color: #0b3c5d; margin: 0 0 6pt 0; }
h2 { font-family: sans-serif; font-size: 13pt; color: #0b3c5d; margin: 0 0 4pt 0; }
p { margin: 0 0 7pt 0; text-align: justify; line-height: 1.3; }
li { margin-bottom: 3pt; }
a { color: #1a5fb4; }
td, th { font-family: sans-serif; font-size: 9.5pt; padding: 3pt 5pt; border: 0.5pt solid #9aa; }
th { background: #e4edf2; }
.cap { font-family: sans-serif; font-size: 8.5pt; color: #555; font-style: italic; }
.note { font-size: 8pt; color: #444; }
"""


def box(page, rect, html):
    page.insert_htmlbox(pymupdf.Rect(rect), html, css=CSS)


def header_footer(page, n, title="A Practical Guide to Personal Finance"):
    box(page, (54, 24, 400, 40), f'<p class="note">{title}</p>')
    box(page, (500, 760, 558, 776), f'<p class="note" style="text-align:right">Page {n}</p>')
    sh = page.new_shape()
    sh.draw_line((54, 42), (558, 42))
    sh.finish(color=(0.75, 0.78, 0.8), width=0.5)
    sh.commit()


def chart_png():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 3), dpi=110)
    ax.bar(["Year 1", "Year 5", "Year 10", "Year 20"], [1.2, 6.9, 16.1, 47.6], color="#1f6f8b")
    ax.set_ylabel("Savings (thousand USD)")
    ax.set_title("Monthly 100 USD invested at 6% per year")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def p_cover(doc, n):
    page = doc.new_page(width=W, height=H)
    sh = page.new_shape()
    sh.draw_rect((0, 0, W, 300))
    sh.finish(fill=(0.04, 0.24, 0.36), color=None)
    sh.commit()
    box(page, (54, 120, 558, 200), '<h1 style="color:#fff;font-size:30pt">A Practical Guide to Personal Finance</h1>')
    box(page, (54, 205, 558, 260), '<p style="color:#dce9f0;font-family:sans-serif;font-size:13pt">Budgeting, saving and investing for young professionals</p>')
    box(page, (54, 340, 558, 520), '<p>This short guide explains how to build a simple monthly budget, create an emergency fund, '
        'and start investing with small amounts. It is written for readers who have just started their first job and want '
        'clear, practical steps rather than complex theory.</p>'
        '<p>Each chapter ends with a checklist. You can read the chapters in any order, but the first two chapters lay the '
        'foundation for everything that follows.</p>')
    box(page, (54, 560, 558, 600), '<p>Read more at <a href="https://example.org/finance-guide">example.org/finance-guide</a>.</p>')
    box(page, (54, 700, 558, 740), f'<p class="note">Sample document for translation testing. Released into the public domain (CC0). Page {n}</p>')


def p_two_columns(doc, n):
    page = doc.new_page(width=W, height=H)
    header_footer(page, n)
    box(page, (54, 60, 558, 100), '<h1>Chapter 1. Know where your money goes</h1>')
    box(page, (54, 110, 300, 700),
        '<p>Most people underestimate how much they spend on small, daily purchases. A coffee on the way to work, a taxi '
        'when it rains and a few online orders each week can add up to a significant share of a monthly salary.</p>'
        '<p>The first step is not to cut spending but to measure it. For one month, write down every expense, however '
        'small. Use a notebook, a spreadsheet or a banking app; the tool matters less than the habit.</p>'
        '<p>At the end of the month, group your expenses into a few categories: housing, food, transport, family support, '
        'entertainment and savings. You will often find one category that is much larger than you expected.<sup>1</sup></p>')
    box(page, (312, 110, 558, 700),
        '<h2>Fixed and variable costs</h2>'
        '<p>Fixed costs, such as rent or loan repayments, stay the same every month. Variable costs, such as groceries or '
        'fuel, change from month to month. Reducing a fixed cost usually requires a bigger decision, for example moving '
        'to a cheaper apartment.</p>'
        '<p>Variable costs are easier to adjust. Small changes, repeated every week, can free up money for your goals '
        'without making life feel restricted.</p>'
        '<p>Review your categories again after three months. Your priorities may change, and your budget should change '
        'with them.</p>')
    box(page, (54, 715, 558, 745), '<p class="note"><sup>1</sup> In our survey of 200 readers, food delivery was the most '
        'underestimated category.</p>')


def p_lists(doc, n):
    page = doc.new_page(width=W, height=H)
    header_footer(page, n)
    box(page, (54, 60, 558, 740),
        '<h1>Chapter 2. Build a simple budget</h1>'
        '<p>A good budget is <b>simple enough to follow</b> and <i>flexible enough to survive surprises</i>. '
        'Many readers like the 50/30/20 rule as a starting point:</p>'
        '<ul><li>50% of income for needs: housing, food, transport and utilities.</li>'
        '<li>30% for wants: travel, hobbies, eating out and gifts.</li>'
        '<li>20% for savings and paying off debt.</li></ul>'
        '<p>If your rent is high, start with a smaller savings rate and increase it by one percentage point every few '
        'months. The direction matters more than the starting number.</p>'
        '<h2>Five steps to start this weekend</h2>'
        '<ol><li>Calculate your net monthly income after tax and insurance.</li>'
        '<li>List your fixed costs and subtract them from your income.</li>'
        '<li>Set a weekly limit for variable spending.</li>'
        '<li>Open a separate account for savings and automate a transfer on payday.</li>'
        '<li>Check your progress every Sunday for ten minutes.</li></ol>'
        '<p>For a free budget template, visit <a href="https://example.org/budget-template">our template page</a>.</p>')


def p_table(doc, n):
    page = doc.new_page(width=W, height=H)
    header_footer(page, n)
    box(page, (54, 60, 558, 120), '<h1>Chapter 3. An example budget</h1>'
        '<p>The table below shows a monthly budget for a person earning 15 million dong after tax.</p>')
    box(page, (54, 130, 558, 420),
        '<table style="width:100%;border-collapse:collapse">'
        '<tr><th>Category</th><th>Amount (million VND)</th><th>Share of income</th><th>Notes</th></tr>'
        '<tr><td>Housing</td><td>4.5</td><td>30%</td><td>Shared apartment near the office</td></tr>'
        '<tr><td>Food</td><td>3.0</td><td>20%</td><td>Mostly cooked at home</td></tr>'
        '<tr><td>Transport</td><td>0.8</td><td>5%</td><td>Motorbike fuel and parking</td></tr>'
        '<tr><td>Family support</td><td>1.5</td><td>10%</td><td>Sent to parents monthly</td></tr>'
        '<tr><td>Wants</td><td>2.2</td><td>15%</td><td>Cafés, books and short trips</td></tr>'
        '<tr><td>Savings</td><td>3.0</td><td>20%</td><td>Emergency fund first</td></tr>'
        '</table>')
    box(page, (54, 430, 558, 450), '<p class="cap">Table 1. Example monthly budget. Figures are rounded.</p>')
    box(page, (54, 470, 558, 740),
        '<p>Notice that savings are treated as a fixed cost. When saving is automatic, you do not need willpower every '
        'month, and the remaining money can be spent without guilt.</p>'
        '<p>If an unexpected expense appears, reduce the wants category first. Only touch the savings line when the '
        'situation is truly urgent.</p>')


def p_chart(doc, n, png):
    page = doc.new_page(width=W, height=H)
    header_footer(page, n)
    box(page, (54, 60, 558, 130), '<h1>Chapter 4. Let time do the work</h1>'
        '<p>Small amounts invested regularly can grow surprisingly large because returns are reinvested.</p>')
    page.insert_image(pymupdf.Rect(86, 140, 526, 360), stream=png)
    box(page, (54, 365, 558, 385), '<p class="cap">Figure 1. Growth of 100 USD invested every month at an average return of 6% per year.</p>')
    box(page, (54, 400, 558, 740),
        '<p>The chart is an illustration, not a forecast. Real markets go up and down, and past returns do not guarantee '
        'future results. Still, the pattern is clear: the earlier you start, the more time your money has to grow.</p>'
        '<p>Before investing, make sure you have an emergency fund that covers three to six months of essential costs. '
        'Investing money you may need next month forces you to sell at a bad time.</p>')


def p_callout(doc, n):
    page = doc.new_page(width=W, height=H)
    header_footer(page, n)
    box(page, (54, 60, 558, 100), '<h1>Chapter 5. Checklist</h1>')
    sh = page.new_shape()
    sh.draw_rect((54, 110, 558, 300))
    sh.finish(fill=(0.93, 0.96, 0.95), color=(0.55, 0.7, 0.65), width=0.8)
    sh.commit()
    box(page, (70, 122, 542, 290),
        '<h2>Key ideas</h2>'
        '<ul><li>Track every expense for one month before changing anything.</li>'
        '<li>Automate savings on the day you receive your salary.</li>'
        '<li>Keep an emergency fund before you invest.</li>'
        '<li>Review your budget every three months.</li></ul>')
    box(page, (54, 320, 558, 740),
        '<p style="font-style:italic;color:#444">“Do not save what is left after spending, but spend what is left after '
        'saving.”</p>'
        '<p>Personal finance is less about knowledge and more about behaviour. The steps in this guide are easy to '
        'understand; the challenge is to repeat them month after month. Start small, be patient, and celebrate progress.</p>'
        '<p>Questions or suggestions? Write to <a href="mailto:hello@example.org">hello@example.org</a>.</p>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=6)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    doc = pymupdf.open()
    png = chart_png()
    makers = [p_cover, p_two_columns, p_lists, p_table, lambda d, n: p_chart(d, n, png), p_callout]
    for i in range(a.pages):
        makers[i % 6 if i < 6 else 1 + (i - 1) % 5](doc, i + 1)
    doc.set_metadata({"title": "A Practical Guide to Personal Finance (sample)", "author": "Sample, CC0"})
    doc.save(a.out, garbage=4, deflate=True)  # gộp ảnh trùng lặp cho file nhỏ
    print(a.out, doc.page_count if not doc.is_closed else "")


if __name__ == "__main__":
    main()
