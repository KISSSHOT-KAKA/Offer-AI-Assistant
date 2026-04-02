import os
import json
import fitz  # 处理 PDF 的翻译官
from paddleocr import PaddleOCR
from openai import OpenAI
import pandas as pd  # 【新增】呼叫表格大管家

# ================= 1. 初始化引擎与大脑 =================
print("⚙️  正在启动 OCR 视觉引擎...")
ocr = PaddleOCR(use_angle_cls=True, lang="ch")

print("🧠 正在连接 LLM 云端大脑...")
client = OpenAI(
    api_key="5fbb6ce1c43e46fa864575b77b911496.FT34Ha4xCfXr2Gga",  # <--- 记得换钥匙！
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

# 提示词紧箍咒
system_prompt = """
【角色】
你是一个极其严谨的 AI 数据提取专家。你的任务是从一段由 OCR 引擎识别出来的、可能带有乱码和错字的杂乱文本中，提取出关键信息并严格按照要求进行【数据标准化 (Data Normalization)】。

【提取字段要求】
请从文本中提取以下信息，并严格遵循对应字段：
【提取字段要求与标准化规则】
1. "candidate_name" (学生姓名)：保持原样提取。
2. "target_institution" (录取学校/公司)：
   - 【标准化】：如果同时存在中英文，优先统一输出【中文全称】（如：宝洁公司、西交利物浦大学）；
   - 如果是纯海外机构/学院，请输出官方英文全称，并修复 OCR 导致的单词粘连问题（如将 P&GGreater 修复为 P&G Greater）。
3. "major_or_position" (录取专业/岗位)：剔除修饰词，保留核心名词。
4. "deadline" (确认截止日期)：
   - 【硬性标准化】：必须将所有提取到的时间，统一转换为 "YYYY-MM-DD" 的标准格式（例如将 "28 May 2026" 转为 "2026-05-28"；将 "2026年4月15日下午18：00" 转为 "2026-04-15"）。
   - 如果没有明确日期，严格填 null。

【处理规则】
1. 如果文本中没有明确包含某个字段的信息，请对应的值填 null，绝不允许猜测或捏造。
2. 请克服 OCR 带来的错别字干扰，结合上下文推断最合理的名词/正确的机构名称。

【输出格式】
严格且仅输出一个合法的 JSON 对象。不要包含任何 Markdown 格式（比如 ```json ），不要输出任何解释性或礼貌性的废话。
"""

folder_path = "offers"
output_folder = "ocr_json_results"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 【新增】准备一个大篮子，用来装所有成功提取的 Offer 数据
all_offers_data = []

print("\n🚀 自动化流水线已就绪，开始批量处理...\n")

# ================= 2. 核心流水线循环 =================
for file_name in os.listdir(folder_path):
    file_path = os.path.join(folder_path, file_name)
    file_ext = os.path.splitext(file_name)[1].lower()

    if file_ext not in ['.pdf', '.jpg', '.jpeg', '.png', '.bmp']:
        continue

    print(f"▶️  正在处理入站文件: 【{file_name}】")

    # -------- 步骤 A: OCR 提取文本 --------
    extracted_texts = []
    if file_ext == '.pdf':
        doc = fitz.open(file_path)
        for page_num in range(doc.page_count):
            page = doc[page_num]
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            temp_img_path = f"temp_{page_num}.png"
            pix.save(temp_img_path)

            result = ocr.ocr(temp_img_path, cls=True)
            if result[0] is not None:
                for line in result[0]:
                    extracted_texts.append(line[1][0])
            os.remove(temp_img_path)
    else:
        result = ocr.ocr(file_path, cls=True)
        if result[0] is not None:
            for line in result[0]:
                extracted_texts.append(line[1][0])

    ocr_raw_data = "\n".join(extracted_texts)

    # -------- 步骤 B: 呼叫大模型进行总结 --------
    if not ocr_raw_data.strip():
        print("   ⚠️ 警告：该文件未提取到任何文字，跳过。\n")
        continue

    response = client.chat.completions.create(
        model="glm-4-flash",
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"这是原始文本，请提取：\n{ocr_raw_data}"}
        ]
    )

    llm_result_str = response.choices[0].message.content.strip()

    # -------- 步骤 C: 清洗与存入大篮子 --------
    try:
        if llm_result_str.startswith("```json"):
            llm_result_str = llm_result_str[7:-3]

        final_dict = json.loads(llm_result_str)

        # 【新增】为了在 Excel 里知道这条数据是哪个文件来的，我们把文件名也塞进字典里
        final_dict['源文件'] = file_name

        # 把这条处理好的字典，扔进咱们的大篮子里
        all_offers_data.append(final_dict)

        print("   ✅ 核心信息提取成功并已入库！")

    except Exception as e:
        print(f"   ❌ 解析大模型结果失败: {e}")

# ================= 3. 【新增】生成高管汇报 Excel =================
print("\n📊 正在生成最终的 Excel 汇总报表...")

if len(all_offers_data) > 0:
    # 召唤 pandas 把大篮子变成一个数据框 (DataFrame)
    df = pd.DataFrame(all_offers_data)

    # 调整一下列的显示顺序，让“源文件”排在最前面，看着更舒服
    columns_order = ['源文件', 'candidate_name', 'target_institution', 'major_or_position', 'deadline']
    # 过滤掉万一大模型多生成的奇葩字段，只保留我们要的
    columns_exist = [col for col in columns_order if col in df.columns]
    df = df[columns_exist]

    # 给表头换个人类能看懂的中文名字
    df.rename(columns={
        'candidate_name': '候选人姓名',
        'target_institution': '录取机构/公司',
        'major_or_position': '录取专业/岗位',
        'deadline': '确认截止日期'
    }, inplace=True)

    # 导出为 Excel 文件！
    excel_path = "Offer汇总报表.xlsx"
    df.to_excel(excel_path, index=False)

    print(f"🎉 报告老板，全自动流水线运行完毕！漂亮的数据报表已保存在当前目录：【{excel_path}】")
else:
    print("⚠️ 报告老板，今天没有提取到任何有效的数据，未生成 Excel。")