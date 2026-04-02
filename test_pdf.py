import os
import fitz  # 呼叫咱们刚装好的 PyMuPDF 翻译官
from paddleocr import PaddleOCR

# 1. 唤醒 AI 员工
ocr = PaddleOCR(use_textline_orientation=True, lang="ch")
pdf_path = "offers/test.pdf"

# 2. 翻译官登场：打开这本 PDF 册子
doc = fitz.open(pdf_path)
print(f"📄 成功打开PDF，这本册子一共有 {doc.page_count} 页！\n")

# 3. 逐页翻阅（一个简单的循环）
for page_num in range(doc.page_count):
    page = doc[page_num]

    # 【核心黑科技：像素光栅化】
    # 深度学习模型不懂 PDF 的排版，只懂像素。
    # 我们用 matrix=fitz.Matrix(2.0, 2.0) 把当前页面强行放大 2 倍，
    # 拍成一张高清照片，这样 OCR 员工才能看清上面的小字！
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)

    # 把这张高清照片临时存到硬盘上
    temp_img_path = f"temp_page_{page_num}.png"
    pix.save(temp_img_path)

    print(f"========== 🔍 正在识别第 {page_num + 1} 页 ==========")

    # 把临时照片交给 OCR 员工去认字
    result = ocr.ocr(temp_img_path)

    # 文本榨汁机
    if result[0] is not None:
        for line in result[0]:
            print(line[1][0])

    # 【架构师的极客习惯：过河拆桥】
    # 每读完一页，立刻把那张临时照片删掉，绝不占用电脑多余的硬盘空间！
    os.remove(temp_img_path)

print("\n✅ 整本 PDF 阅读完毕！")