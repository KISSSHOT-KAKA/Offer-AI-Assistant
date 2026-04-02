import os
import json
from openai import OpenAI

# 1. 建立通信
client = OpenAI(
    api_key="5fbb6ce1c43e46fa864575b77b911496.FT34Ha4xCfXr2Gga",
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

system_prompt = """
【角色】
你是一个极其严谨的 AI 数据提取专家。你的任务是从一段由 OCR 引擎识别出来的、可能带有乱码和错字的杂乱文本中，提取出关键信息。

【提取字段要求】
1. "candidate_name" (学生姓名)
2. "target_institution" (录取学校 或 招聘公司名称)
3. "major_or_position" (录取专业 或 岗位名称)
4. "deadline" (提交/确认截止日期，如果没有则填 null)

【处理规则】
1. 如果文本中没有明确包含某个字段，请对应的值填 null，绝不允许猜测。
2. 克服 OCR 带来的错别字干扰，结合上下文推断最合理的名词。

【输出格式】
严格且仅输出一个合法的 JSON 对象。不要包含任何 Markdown 格式（比如 ```json ），不要输出任何解释性废话。
"""

input_folder = "ocr_json_results"

print("🚀 启动全自动 AI 总结流水线...\n")

# 2. 遍历 OCR 提取出来的所有 JSON 文件
for file_name in os.listdir(input_folder):
    if not file_name.endswith('.json'):
        continue

    file_path = os.path.join(input_folder, file_name)

    # 读出里面的脏乱文本
    with open(file_path, 'r', encoding='utf-8') as f:
        ocr_raw_data = f.read()

    print(f"📡 正在呼叫大脑处理: {file_name}")

    # 3. 呼叫大模型
    response = client.chat.completions.create(
        model="glm-4-flash",
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"这是原始文本，请提取：\n{ocr_raw_data}"}
        ]
    )

    llm_result_str = response.choices[0].message.content.strip()

    # 4. 把大模型返回的字符串，解析成真正的 Python 字典，打印出来
    try:
        # 有时候大模型还是会手贱加个 ```json，我们用代码强行剥掉
        if llm_result_str.startswith("```json"):
            llm_result_str = llm_result_str[7:-3]

        final_dict = json.loads(llm_result_str)

        print("✅ 提取成功：")
        print(f"   👤 姓名: {final_dict.get('candidate_name')}")
        print(f"   🏢 机构: {final_dict.get('target_institution')}")
        print(f"   💼 岗位/专业: {final_dict.get('major_or_position')}")
        print(f"   ⏰ 截止时间: {final_dict.get('deadline')}")
        print("-" * 50)

    except Exception as e:
        print(f"❌ 哎呀，大模型胡言乱语了，解析失败: {e}")
        print("-" * 50)