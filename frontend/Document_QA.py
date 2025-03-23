# 基于文档的问答
import time
import re
import streamlit as st
import pandas as pd
from server.stores.chat_store import CHAT_MEMORY
from llama_index.core.llms import ChatMessage, MessageRole
from server.engine import create_query_engine
from server.stores.config_store import CONFIG_STORE

def perform_query(prompt):
    if not st.session_state.query_engine:
        print("索引尚未初始化")
    if (not prompt) or prompt.strip() == "":
        print("查询文本是必需的")
    try:
        query_response = st.session_state.query_engine.query(prompt)
        return query_response
    except Exception as e:
        # print(f"处理查询时发生错误: {e}")
        print(f"处理查询时发生错误: {type(e).__name__}: {e}")

# https://github.com/halilergul1/QA-app
def simple_format_response_and_sources(response):
    primary_response = getattr(response, 'response', '')
    output = {"response": primary_response}
    sources = []
    if hasattr(response, 'source_nodes'):
        for node in response.source_nodes:
            node_data = getattr(node, 'node', None)
            if node_data:
                metadata = getattr(node_data, 'metadata', {})
                text = getattr(node_data, 'text', '')
                text = re.sub(r'\n\n|\n|\u2028', lambda m: {'\n\n': '\u2028', '\n': ' ', '\u2028': '\n\n'}[m.group()], text)
                source_info = {
                    "file": metadata.get('file_name', 'N/A'),
                    "page": metadata.get('page_label', 'N/A'),
                    "text": text
                }
                sources.append(source_info)
    output['sources'] = sources
    return output

def chatbox():

    # 加载问答历史
    messages = CHAT_MEMORY.get() 
    if len(messages) == 0:
        # 初始化问答记录
        CHAT_MEMORY.put(ChatMessage(role=MessageRole.ASSISTANT, content="欢迎提问知识库中的任何问题"))
        messages = CHAT_MEMORY.get()

    # 显示问答记录
    for message in messages: 
        with st.chat_message(message.role):
            st.write(message.content)

    if prompt := st.chat_input("请输入你的问题"): # 提示用户输入问题，然后添加到消息历史
        with st.chat_message(MessageRole.USER):
            st.write(prompt)
            CHAT_MEMORY.put(ChatMessage(role=MessageRole.USER, content=prompt))
        with st.chat_message(MessageRole.ASSISTANT):
            with st.spinner("思考中..."):
                start_time = time.time()
                response = perform_query(prompt)
                end_time = time.time()
                query_time = round(end_time - start_time, 2)
                if response is None:
                    st.write("无法生成答案。")
                else:
                    response_text = st.write_stream(response.response_gen)
                    st.write(f"耗时 {query_time} 秒")
                    details_title = f"找到 {len(response.source_nodes)} 个文档"
                    with st.expander(
                            details_title,
                            expanded=False,
                    ):
                        source_nodes = []
                        for item in response.source_nodes:
                            node = item.node
                            score = item.score
                            title = node.metadata.get('file_name', None)
                            if title is None:
                                title = node.metadata.get('title', 'N/A') # 如果文档是网页，则使用标题
                                continue
                            page_label = node.metadata.get('page_label', 'N/A')
                            text = node.text
                            short_text = text[:50] + "..." if len(text) > 50 else text
                            source_nodes.append({"标题": title, "页码": page_label, "文本": short_text, "得分": f"{score:.2f}"})
                        df = pd.DataFrame(source_nodes)
                        st.table(df)
                    # 将答案存储在聊天历史中
                    CHAT_MEMORY.put(ChatMessage(role=MessageRole.ASSISTANT, content=response_text))

                    
def main():
    st.header("查询")
    if st.session_state.llm is not None:
        current_llm_info = CONFIG_STORE.get(key="current_llm_info")
        current_llm_settings = CONFIG_STORE.get(key="current_llm_settings")
        st.caption("LLM `" + current_llm_info["service_provider"] + "` `" + current_llm_info["model"] + 
                   "` 响应模式 `" + current_llm_settings["response_mode"] + 
                   "` Top K `" + str(current_llm_settings["top_k"]) + 
                   "` 温度 `" + str(current_llm_settings["temperature"]) + 
                   "` 重新排序 `" + str(current_llm_settings["use_reranker"]) + 
                   "` Top N `" + str(current_llm_settings["top_n"]) + 
                   "` 重新排序模型 `" + current_llm_settings["reranker_model"] + "`"
                   )
        if st.session_state.index_manager is not None:
            if st.session_state.index_manager.check_index_exists():
                st.session_state.index_manager.load_index()
                st.session_state.query_engine = create_query_engine(
                    index=st.session_state.index_manager.index, 
                    use_reranker=current_llm_settings["use_reranker"], 
                    response_mode=current_llm_settings["response_mode"], 
                    top_k=current_llm_settings["top_k"],
                    top_n=current_llm_settings["top_n"],
                    reranker=current_llm_settings["reranker_model"])
                print("索引已加载，查询引擎已创建")
                chatbox()
            else:
                print("索引尚不存在")
                st.warning("你的知识库是空的。请先上传一些文档。")
        else:
            print("IndexManager 尚未初始化。")
            st.warning("请先上传文档到你的知识库。")
    else:
        st.warning("请先配置 LLM。")

main()
