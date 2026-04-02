import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
import pandas as pd
import tempfile
import os
import base64
import json

st.set_page_config(page_title="Offer 智能解析系统", page_icon="🎓", layout="wide")


# --- 1. 加载大模型 (纯云端架构，彻底抛弃本地 OCR) ---
@st.cache_resource
def load_ai_models():
    # 只要一个智谱大模型的客户端就够了
    client = OpenAI(
        api_key=st.secrets["ZHIPU_API_KEY"],
        base_url="https://open.bigmodel.cn/api/paas/v4/"
    )
    return client


try:
    client = load_ai_models()
except Exception as e:
    st.error("🚨 模型加载失败了！底层的真实报错信息如下：")
    st.code(str(e))  # 把真正的内鬼暴露出来！
    st.write("如果上面写着 KeyError: 'ZHIPU_API_KEY'，说明 Streamlit 真的没读到密码；如果是别的，说明问题出在别的库上。")
    st.stop()

# --- 辅助函数：图片转 Base64 编码 ---
def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


# --- 2. 核心大模型解析逻辑 (GLM-4V 视觉模型) ---
def extract_info_with_glm4v(base64_image):
    try:
        response = client.chat.completions.create(
            model="glm-4v",  # 调用智谱视觉模型
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "你是一个专业的HR助手。请阅读这张Offer图片，提取以下信息并严格输出为纯JSON格式字典。不要输出任何Markdown标记（如```json），不要任何废话，直接输出JSON本身：\n"
                                    "必须包含的键：姓名, 公司, 岗位, 薪水, 截止日期。\n"
                                    "如果图片中某项信息找不到，请填入 '未知'。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        )

        # 获取大模型返回的文本并清理可能带有的 Markdown 格式
        result_str = response.choices[0].message.content.strip()
        if result_str.startswith("```json"):
            result_str = result_str[7:]
        if result_str.endswith("```"):
            result_str = result_str[:-3]

        return json.loads(result_str.strip())

    except Exception as e:
        return {"姓名": "解析失败", "公司": "解析失败", "岗位": "解析失败", "薪水": str(e), "截止日期": "未知"}


# --- 3. 网页 UI 界面 ---
st.title("🎓 智能 Offer 解析系统 (云端极速版)")
st.markdown("上传 Offer 文件 (图片或 PDF)，AI 视觉模型将自动提取核心信息并生成 Excel。")

uploaded_files = st.file_uploader("请选择文件", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 开始一键极速解析"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        results = []
        total_files = len(uploaded_files)

        with tempfile.TemporaryDirectory() as temp_dir:
            for i, uploaded_file in enumerate(uploaded_files):
                file_name = uploaded_file.name
                file_ext = os.path.splitext(file_name)[1].lower()
                status_text.info(f"⏳ 正在呼叫智谱大模型阅读: {file_name} ({i + 1}/{total_files})...")

                # 安全的临时文件名
                safe_temp_name = f"temp_upload_{i}{file_ext}"
                temp_file_path = os.path.join(temp_dir, safe_temp_name)

                with open(temp_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                extracted_data = {}

                # 4. 根据文件类型处理并发送给大模型
                if file_ext == '.pdf':
                    doc = fitz.open(temp_file_path)
                    try:
                        if doc.page_count > 0:
                            page = doc[0]  # PDF通常核心信息在第一页，我们取第一页转图
                            mat = fitz.Matrix(2.0, 2.0)
                            pix = page.get_pixmap(matrix=mat)
                            temp_img = os.path.join(temp_dir, f"page_0.png")
                            pix.save(temp_img)

                            # 转码并发送
                            base64_img = encode_image_to_base64(temp_img)
                            extracted_data = extract_info_with_glm4v(base64_img)
                    finally:
                        doc.close()
                else:
                    # 直接是图片的话
                    base64_img = encode_image_to_base64(temp_file_path)
                    extracted_data = extract_info_with_glm4v(base64_img)

                # 将文件名加入结果中，防止混淆
                extracted_data["来源文件"] = file_name
                results.append(extracted_data)

                progress_bar.progress((i + 1) / total_files)

        status_text.success("✅ 全部解析完成！快去下载吧！")

        # --- 5. 生成并下载 Excel ---
        if results:
            df = pd.DataFrame(results)
            # 重新排列列的顺序，更美观
            cols = ["来源文件", "姓名", "公司", "岗位", "薪水", "截止日期"]
            existing_cols = [c for c in cols if c in df.columns]
            df = df[existing_cols]

            st.dataframe(df)

            excel_path = os.path.join(tempfile.gettempdir(), "offer_summary.xlsx")
            df.to_excel(excel_path, index=False)
            with open(excel_path, "rb") as f:
                st.download_button(
                    label="📥 一键下载 Excel 汇总报表",
                    data=f,
                    file_name="Offer汇总报表.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )