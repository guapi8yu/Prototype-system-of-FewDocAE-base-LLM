import streamlit as st
import re
import ast
import json

# 设置宽屏模式
st.set_page_config(layout="wide")

# 自定义CSS样式（浅色风格化）
st.markdown("""
    <style>
        /* 全局背景和字体 */
        body {
            background-color: #f0f4f8;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        /* 页面标题 */
        h1 {
            color: #1d5fa6;
            font-size: 34px;
            font-weight: 600;
            margin-bottom: 20px;
        }

        /* 控制面板样式 */
        .stButton>button {
            background-color: #E3F2FD;
            color: black;
            font-weight: 600;
            border-radius: 14px;
            height: 48px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }

        .stButton>button:hover {
            background-color: #0056b3;
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }

        .stTextArea>textarea {
            border-radius: 14px;
            border: 1px solid #e2e8f0;
            background-color: #ffffff;
            font-size: 14px;
            padding: 12px;
        }

        .stSelectbox>div {
            border-radius: 14px;
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            padding: 10px;
        }

        /* 高亮文本 */
        .highlight {
            color: #007bff;
            font-weight: bold;
            background-color: #e1f5fe;
            padding: 5px 14px;
            border-radius: 6px;
        }

        .stText {
            color: #333;
            font-size: 14px;
        }

        /* 栅格布局 */
        .stColumns {
            gap: 20px;
        }

        /* 弹出框 */
        .stExpander {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        /* Spinner动画 */
        .css-1qgcyf7 {
            background-color: #007bff;
            border-radius: 14px;
        }

        /* 控制面板 */
        .stContainer {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 14px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }

        .stColumns>div {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 14px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }

        .stMetric>div {
            background-color: #f8fafc;
            border-radius: 14px;
            padding: 10px 16px;
            font-weight: 600;
        }

        /* 信息框 */
        .stInfo>div {
            background-color: #e3f2fd;
            border-radius: 8px;
            padding: 12px;
            font-size: 14px;
        }

        .stError>div {
            background-color: #ffe0e0;
            border-radius: 8px;
            padding: 12px;
            font-size: 14px;
        }

    </style>
""", unsafe_allow_html=True)


# 初始化session状态
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = []
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "selected_model" not in st.session_state:  # 新增模型选择状态
    st.session_state.selected_model = "基于多智能体系统的FewDocAE模型"


def main():
    st.title("📑 基于大语言模型的少样本篇章级事件论元抽取系统 --- Few-Shot Document-Level Event Argument Extraction System base on LLM")
    st.markdown('---')

    # 文件上传区域
    with st.container():
        uploaded_file = st.file_uploader("请选择JSONL格式数据文件", type=["jsonl"],
                                         help="支持格式：每行包含event_type, argument_type, event_definition, support_word, support_label, query_word的JSON对象")
        if not uploaded_file:
            st.info("👋 请先上传数据文件并开始抽取")

    # 主内容区域
    col1, col2 = st.columns([0.8, 3], gap="large")

    with col1:  # 控制面板（新增模型选择）
        with st.container():
            st.subheader("操控面板")
            st.markdown("---")

            # 新增模型选择器
            selected_model = st.selectbox("选择处理模型",
                                          options=["融合提示压缩的FewDocAE模型", "基于多智能体系统的FewDocAE模型"],
                                          index=1 if st.session_state.selected_model == "基于多智能体系统的FewDocAE模型" else 0,
                                          key="model_selector")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("▶️ 开始抽取", use_container_width=True, type="primary"):
                    handle_start(uploaded_file)
            with c2:
                if st.button("⏹️ 停止程序", use_container_width=True):
                    handle_stop()

            st.markdown("---")
            nav_col1, nav_col2 = st.columns(2)
            with nav_col1:
                if st.button("⬅️ 上一条", use_container_width=True):
                    handle_previous()
            with nav_col2:
                if st.button("➡️ 下一条", use_container_width=True):
                    handle_next()

            st.markdown("---")
            current_idx = st.number_input("跳转到指定序号",
                                          min_value=1,
                                          max_value=len(
                                              st.session_state.extracted_data) if st.session_state.extracted_data else 1,
                                          value=st.session_state.current_index + 1)
            if st.button("跳转"):
                handle_jump(current_idx - 1)

    with col2:  # 数据展示
        if st.session_state.extracted_data:
            current_data = st.session_state.extracted_data[st.session_state.current_index]
            display_data(current_data)


# 数据展示组件
def display_data(data):
    with st.container():
        cols = st.columns(2)
        cols[0].metric("当前序号", f"#{data[2]}")
        cols[1].metric("总数据量", len(st.session_state.extracted_data))

        st.markdown("---")

        # 核心数据展示
        with st.expander("📌 事件类型详情", expanded=True):
            st.markdown(f'**事件类型**:\n<div class="highlight">{data[3]}</div>', unsafe_allow_html=True)
            st.markdown(f'**论元类型**:\n<div class="highlight">{data[4]}</div>', unsafe_allow_html=True)

        st.subheader("📄 原始文档")
        st.text_area("document_content",
                     value=data[0],
                     height=300,
                     label_visibility="collapsed")

        st.subheader("✅ 抽取结果")
        st.json(data[1] if data[1] else {"status": "等待抽取..."})


# 业务逻辑函数 --------------------------------------------------
def handle_start(uploaded_file):
    if uploaded_file:
        with st.spinner('🚀 正在抽取数据，请稍候...'):
            try:
                file_content = uploaded_file.read()
                data_list = read_jsonl_from_bytes(file_content)
                process_data(data_list)
                st.session_state.current_index = 0
                st.success(f"成功处理 {len(data_list)} 条数据！")
            except Exception as e:
                st.error(f"处理失败: {str(e)}")
    else:
        st.warning("⚠️ 请先上传数据文件")


def handle_stop():
    st.session_state.extracted_data = []
    st.session_state.current_index = 0
    st.info("🛑 已停止并重置系统状态")


def handle_previous():
    if st.session_state.current_index > 0:
        st.session_state.current_index -= 1
        st.rerun()


def handle_next():
    if st.session_state.current_index < len(st.session_state.extracted_data) - 1:
        st.session_state.current_index += 1
        st.rerun()


def handle_jump(index):
    if 0 <= index < len(st.session_state.extracted_data):
        st.session_state.current_index = index
        st.rerun()


# 数据处理函数
def read_jsonl_from_bytes(file_content):
    data_list = []
    file_content_str = file_content.decode("utf-8")
    for line in file_content_str.splitlines():
        data = json.loads(line.strip())
        data_list.append(data)
    return data_list


def process_data(data_list):
    st.session_state.extracted_data = []
    for data in data_list:
        # 根据选择的模型调用不同方法（用户需用户自行加载自己的抽取模型）
        if st.session_state.selected_model == "基于多智能体系统的FewDocAE模型":
            output_dic = model1(  # 模型1
                data['event_type'],
                data['argument_type'],
                data['event_definition'],
                data['support_word'],
                data['support_label'],
                data['query_word']
            )
        else:  # 融合提示压缩版本
            output_dic = model2(  # 需用户自行加载自己的抽取模型 ；模型2
                data['event_type'],
                data['argument_type'],
                data['event_definition'],
                data['support_word'],
                data['support_label'],
                data['query_word']
            )

        st.session_state.extracted_data.append((
            data['query_word'],
            output_dic,
            len(st.session_state.extracted_data) + 1,
            data['event_type'],
            data['argument_type']
        ))





if __name__ == "__main__":
    main()
