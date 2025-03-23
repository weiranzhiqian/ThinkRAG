import time
import pandas as pd
import streamlit as st
from server.utils.file import save_uploaded_file, get_save_dir

def handle_file():

    st.header("加载文件")
    st.caption("加载PDF、DOCX、TXT等文件以创建知识库索引。")
    
    with st.form("my-form", clear_on_submit=True):
        st.session_state.selected_files = st.file_uploader("上传文件： ", accept_multiple_files=True, label_visibility="hidden")
        submitted = st.form_submit_button(
            "加载",
            help="选择文件后，点击此处加载。",
            )
        if len(st.session_state.selected_files) > 0 and submitted:
            print("开始上传文件...")
            print(st.session_state.selected_files)
            for selected_file in st.session_state.selected_files:
                with st.spinner(f"上传 {selected_file.name} 中..."):
                    save_dir = get_save_dir()
                    save_uploaded_file(selected_file, save_dir)
                    st.session_state.uploaded_files.append({"name": selected_file.name, "type": selected_file.type, "size": selected_file.size})
            st.toast('✔️ 上传成功', icon='🎉')

    if len(st.session_state.uploaded_files) > 0:
        with st.expander(
                "以下文件已成功上传。",
                expanded=True,
        ):
            df = pd.DataFrame(st.session_state.uploaded_files)
            st.dataframe(
                df,
                column_config={
                    "name": "文件名",
                    "size": st.column_config.NumberColumn(
                        "size", format="%d 字节",
                    ),
                    "type": "类型",
                },
                hide_index=True,
            )

    with st.expander(
            "文本分割器设置",
            expanded=True,
    ):
        cols = st.columns(2)
        chunk_size = cols[0].number_input("单个文本块的最大长度： ", 1, 4096, st.session_state.chunk_size)
        chunk_overlap = cols[1].number_input("相邻文本重叠长度： ", 0, st.session_state.chunk_size, st.session_state.chunk_overlap)

    if st.button(
        "保存",
        disabled=len(st.session_state.uploaded_files) == 0,
        help="上传文件后，点击此处生成索引并将其保存到知识库。",
    ):
        print("生成索引...")
        with st.spinner(text="正在加载文档并构建索引，可能需要一两分钟"):
            st.session_state.index_manager.load_files(st.session_state.uploaded_files, chunk_size, chunk_overlap)
            st.toast('✔️ 知识库索引生成完成', icon='🎉')
            st.session_state.uploaded_files = []
            time.sleep(4)
            st.rerun()

handle_file()
