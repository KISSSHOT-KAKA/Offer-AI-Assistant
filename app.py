import streamlit as st
import os
import json
import fitz  # PyMuPDF
import pandas as pd
from paddleocr import PaddleOCR
from openai import OpenAI
import tempfile
from io import BytesIO

# ================= 1. 网页全局配置 (UI 门面) =================
st.set_page_config(page_title="Offer 智能解析系统", page_icon="🎓", layout="wide")
st.title("🎓 Offer 智能解析与管理系统")
st.markdown("上传学生的 Offer 文件 (支持 PDF/图片)，AI 将自动提取、清洗并生成标准化的 Excel 报表。")


# ================= 2. 核心引擎缓存加载 (极速体验架构) =================
# @st.cache_resource 是架构师的神技：保证 AI 模型只在服务器启动时加载一次，避免每次点击网页都重新加载！
@st.cache_resource
def load_ai_models():
    # 强制开启 use_angle_cls=True，消灭倒立/歪斜图片的克星
    ocr_engine = PaddleOCR(use_angle_cls=True, lang="ch")
    llm_client = OpenAI(
        api_key=st.secrets["ZHIPU_API_KEY"], # <-- 换成这个“代号”  # <--- 🚨 请在这里填入你的智谱 API Key
        base_url="https://open.bigmodel.cn/api/paas/v4/"
    )
    return ocr_engine, llm_client


ocr, client = load_ai_models()

# 数据标准化的 Prompt 紧箍咒 (V2.0 数据治理版)
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

# ================= 3. 酷炫的用户交互界面 (UI 交互层) =================
# 拖拽上传组件：允许一次性选中多个文件
uploaded_files = st.file_uploader("📂 请拖拽或点击选择 Offer 文件", accept_multiple_files=True,
                                  type=['png', 'jpg', 'jpeg', 'bmp', 'pdf'])

# 只有当用户点击按钮时，流水线才开始轰鸣
if st.button("🚀 一键智能解析并生成报表", type="primary"):
    if not uploaded_files:
        st.warning("⚠️ 报告老板：请先上传至少一个文件哦！")
    else:
        all_offers_data = []

        # 建立动态进度条和状态提示
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_files = len(uploaded_files)

        # 【架构师黑科技】使用临时文件夹 (TemporaryDirectory)
        # 因为网页上传的文件是内存字节流，而 PaddleOCR 和 PyMuPDF 需要真实的硬盘路径
        with tempfile.TemporaryDirectory() as temp_dir:
            for i, uploaded_file in enumerate(uploaded_files):
                file_name = uploaded_file.name
                file_ext = os.path.splitext(file_name)[1].lower()
                status_text.info(f"⏳ 正在处理: {file_name} ({i + 1}/{total_files})...")

                # 🚨【架构师黑科技：狸猫换太子】🚨
                # 为了防止 OpenCV 读取中文路径时报 TypeError 返回 None
                # 我们在硬盘上强制使用纯英文的序号命名，避开所有特殊字符！
                safe_temp_name = f"temp_upload_{i}{file_ext}"
                temp_file_path = os.path.join(temp_dir, safe_temp_name)

                with open(temp_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # -------- 步骤 A: 底层视觉引擎榨汁 (OCR) --------
                    # ---- 步骤 A: OCR 榨汁 ----
                    extracted_texts = []
                    if file_ext == '.pdf':
                        # 建议使用 with 语句或者手动 close
                        doc = fitz.open(temp_file_path)
                        try:
                            for page_num in range(doc.page_count):
                                page = doc[page_num]
                                mat = fitz.Matrix(2.0, 2.0)
                                pix = page.get_pixmap(matrix=mat)
                                temp_img = os.path.join(temp_dir, f"page_{page_num}.png")
                                pix.save(temp_img)

                                result = ocr.ocr(temp_img, cls=True)
                                if result[0]:
                                    for line in result[0]:
                                        extracted_texts.append(line[1][0])

                                # 识别完图片立即删掉单页图片，释放压力
                                if os.path.exists(temp_img):
                                    os.remove(temp_img)
                        finally:
                            # 🚨 无论成功失败，一定要关闭 PDF 文件句柄！
                            doc.close()
                    else:
                        # 直接处理图片
                        result = ocr.ocr(temp_file_path, cls=True)
                        if result[0]:
                            extracted_texts.extend([line[1][0] for line in result[0]])

                ocr_raw_data = "\n".join(extracted_texts)

                # -------- 步骤 B: 呼叫云端大脑 (LLM) --------
                if ocr_raw_data.strip():
                    try:
                        response = client.chat.completions.create(
                            model="glm-4-flash",
                            temperature=0.1,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": f"提取数据：\n{ocr_raw_data}"}
                            ]
                        )
                        llm_result_str = response.choices[0].message.content.strip()

                        # 强行脱掉大模型可能加上的 Markdown 外衣
                        if llm_result_str.startswith("```json"):
                            llm_result_str = llm_result_str[7:-3]
                        elif llm_result_str.startswith("```"):
                            llm_result_str = llm_result_str[3:-3]

                        final_dict = json.loads(llm_result_str)
                        final_dict['源文件'] = file_name  # 记录出处
                        all_offers_data.append(final_dict)

                    except Exception as e:
                        st.error(f"❌ {file_name} 被大模型解析失败: {e}")
                else:
                    st.warning(f"⚠️ {file_name} 未发现任何有效文字，已跳过。")

                # 推进进度条
                progress_bar.progress((i + 1) / total_files)

        # ================= 4. 数据展示与无痕下载 (业务收口) =================
        status_text.success("🎉 报告老板，所有文件处理完毕！")

        if all_offers_data:
            # 转换为 DataFrame
            df = pd.DataFrame(all_offers_data)
            columns_order = ['源文件', 'candidate_name', 'target_institution', 'major_or_position', 'deadline']
            df = df[[c for c in columns_order if c in df.columns]]
            df.rename(columns={
                'candidate_name': '候选人姓名',
                'target_institution': '录取机构/公司',
                'major_or_position': '录取专业/岗位',
                'deadline': '确认截止日期'
            }, inplace=True)

            # 在前端渲染精美的数据表格
            st.subheader("📊 识别结果预览")
            st.dataframe(df, use_container_width=True)

            # 【架构师黑科技】前端无缝下载 Excel
            # 不把 Excel 存到服务器硬盘，而是直接生成内存字节流给用户下载，绝对的安全且不留垃圾！
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            processed_data = output.getvalue()

            st.download_button(
                label="📥 一键下载 Excel 汇总报表",
                data=processed_data,
                file_name="Offer智能汇总表.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )