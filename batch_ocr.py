import os
import json
import fitz  # 处理 PDF 的翻译官
from paddleocr import PaddleOCR

# 1. 唤醒咱们的AI员工
ocr = PaddleOCR(use_textline_orientation=True, lang="ch")

# 2. 设定好输入和输出的文件夹
folder_path = "offers"
output_folder = "ocr_json_results"

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 3. 开始遍历文件夹里的每一个文件
for file_name in os.listdir(folder_path):
    file_path = os.path.join(folder_path, file_name)

    # 架构师思维：用文件后缀名来做分流处理
    file_ext = os.path.splitext(file_name)[1].lower()

    print(f"\n========== 🔍 正在处理: {file_name} ==========")

    # 准备好装文字的篮子
    doc_data = {
        "file_source": file_name,
        "content_list": []
    }

    # 分支 A：如果遇到的是 PDF 文件
    if file_ext == '.pdf':
        doc = fitz.open(file_path)
        for page_num in range(doc.page_count):
            page = doc[page_num]
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            temp_img_path = f"temp_page_{page_num}.png"
            pix.save(temp_img_path)

            result = ocr.ocr(temp_img_path)
            if result[0] is not None:
                for line in result[0]:
                    doc_data["content_list"].append(line[1][0])
            os.remove(temp_img_path)

    # 分支 B：如果遇到的是常见的图片格式
    elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp']:
        result = ocr.ocr(file_path)
        if result[0] is not None:
            for line in result[0]:
                doc_data["content_list"].append(line[1][0])

    # 分支 C：遇到不认识的文件，直接跳过
    else:
        print(f"⚠️ 无法处理的文件格式，跳过: {file_name}")
        continue

    # 将提取到的所有文字打包成 JSON
    json_path = os.path.join(output_folder, file_name + ".json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(doc_data, f, ensure_ascii=False, indent=4)

    print(f"✅ 搞定！结构化 JSON 已存入: {json_path}")

print("\n🚀 恭喜！所有文件处理完毕！数据流水线运行结束！")