#from llama_index import QueryEngine
from llama_index.core import Settings, Document, ListIndex
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.nvidia import NVIDIAEmbedding
from llama_index.llms.nvidia import NVIDIA
import streamlit as st
import os

from rag.document_processors import load_multimodal_data, load_data_from_directory
#from utils import set_environment_variables

from PIL import Image
from db.instr import student_insert_query
from db.exam_helper import get_org_exam_name_info, db_engine_initialize
from db.questions import insert_questions
from db.answers_grading import collect_student_answers
import sqlite3
import pandas as pd
from agents.agent_sage import exam_sage_settings
from agents.agent_sage_student import exam_sage_student_settings
from rag.vector_db import vector_db_indexing

#from agents.nemoguard import call_nemo

# MYMY
import sys
import logging
from loguru import logger
from util.logutil import configure_logging, LoggingContextManager, get_bound_logger, logger_wraps

logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True)

logger.add("Mymy_log.log", format="{time} | {level} | {message}", level="INFO")


db_table = "students" #임시로 - 이걸 불러온다


NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')
print(f'ncidia key: {NVIDIA_API_KEY}')  # 나중 삭제

# Set up the page configuration
st.set_page_config(
    layout="wide",
    menu_items={
        "Get help": "https://github.com/gigit0000",
        "Report a bug": "https://github.com/gigit0000",
        "About": """
        Exam Taker Screen on Exam Sage\n
        Developed by William Song\n
        For NVIDIA Contest\n
        Powered by NVIDIA and LlamaIndex 
        """,
    },
)



# Create index from documents
@st.cache_resource
def create_index(_documents):
    # vector_store = MilvusVectorStore(
    #         host = "127.0.0.1",
    #         port = 19530,
    #         dim = 4096 #original for e5-v5 1024
    # )
    # # vector_store = MilvusVectorStore(uri="./milvus_demo.db", dim=1024, overwrite=True) #For CPU only vector store
    # storage_context = StorageContext.from_defaults(vector_store=vector_store)
    # logger.debug("ready to return vector DB index")
    # return VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    return vector_db_indexing(_documents)

#이게 되는데? return은 못받는다
@st.cache_resource
def initialize_agent_settings(student_name, org_exam_name):
    exam_sage_student_settings(student_name, org_exam_name)
    

@st.cache_resource
def get_org_exam_name(name, organization, exam_name):
    db_engine_initialize()
    #= get_org_exam_name_info(name, organization, exam_name)
    return get_org_exam_name_info(name, organization, exam_name)

    
@st.cache_resource
def get_data_from_db(query):
    try:
        conn = sqlite3.connect("examsage.db")  # Replace with your DB connection
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except:
        pass    



# @st.cache_resource
# def show_questions():

#     conn = sqlite3.connect('examsage00.db')

#     # Query data

#     query = "SELECT * FROM questions"

#     df = pd.read_sql(query, conn)

#     # Close the connection

#     conn.close()

#     return df




# Main function to run the Streamlit app
def main():


    
    print(f'몇 번이 언제 실행되나??????')
    #rerun을 하면 2번 실행된다. 어떻게 처리하나???

    # Navigation control between pages
    if "page" not in st.session_state:
        st.session_state.page = "input_form"
        
    if "org_exam_name" not in st.session_state:
        st.session_state["org_exam_name"] = None

    # Page 1: User Input Form
    if st.session_state.page == "input_form":
        
        st.title("The exam is ready")
        st.markdown(
            "Welcome to Exam Sage for you exam. I'm your exam assistant. You can ask me questions and I'll give you apporopiate feedback.")
        st.markdown(
            "Enter your information below. If you're ready, please press the button to start the exam.")

        with st.form("user_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")  # 여기에 organization과 exam name을 넣자
            organization = st.text_input("Organization").lower()
            exam_name = st.text_input("Exam Name").lower()
            student_id = st.text_input(
                "Student ID or any verifiable ID (optional)")


            submit_button = st.form_submit_button("Start")

        if submit_button:
            if name and email and organization and exam_name:
                # test phase comment
                # save_user_info(name, email, student_id, regi_number)
                student_insert_query(
                    db_table, name, email, organization, exam_name, student_id)
                st.session_state.page = "llm_communication"

                st.session_state.org_exam_name = get_org_exam_name(name,organization, exam_name)
                if st.session_state.org_exam_name[0] == 'Invalid':
                    st.error("Kindly fill correct organization and exam name")
                st.success("Information saved! Moving to the next page...")
                initialize_agent_settings(name, st.session_state.org_exam_name[0]) #수정필요
                # st.rerun()  #임시로 코멘트 처리
            else:
                st.error("Kindly complete all required fields")
     
    #임시로 막음            
    #if st.session_state.page == "llm_communication":
    
    

    col1, col2 = st.columns([2, 1])
    
    with col1:
        # instructor table에 image path 추가
        if 'image_path' in st.session_state:
            image = Image.open(st.session_state.image_path)
            st.image(image, use_column_width=True)

        if 'org_exam_name' not in st.session_state or st.session_state.org_exam_name is None:
            st.session_state.org_exam_name = [""]
        # 기관명과 시험명을 불러온다

        st.title(st.session_state.org_exam_name[0])


        
        data = get_data_from_db(f'SELECT id, questions FROM {st.session_state.org_exam_name[0]}')
        st.dataframe(data)

        # df = show_questions()
        # st.dataframe(df)

        st.session_state.next_col = True
        

        
        
    
    with col2:
        st.markdown("""
                    ### Now, the exam started.
                    Read your questions carefully and enter your answers here.
                    I can answer your questions and give hints for the questions your instructor allowed. Also you can feel free to ask me for information you're searching for with the question number, but it is not allowed to ask me the answers for the questions.
                    
                    Everything is done, please click **"Submit"** button. Then the grading will be started!
                    """)
        if st.session_state.next_col:
            st.header("Chat")
            if 'history' not in st.session_state:
                st.session_state['history'] = []
            


            # Create documents in memory
            documents = [
                Document(text=""),
                Document(text=""),
                # Add more documents as needed
                ]
            if 'index' not in st.session_state:
                st.session_state['index'] = ListIndex.from_documents(documents)
            #index = ListIndex.from_documents(documents)
            query_engine = st.session_state['index'].as_query_engine(similarity_top_k=20, streaming=True)
            logger.debug("as_query_engine CALLED")
            logger.debug(f"st.session_state: {st.session_state}")
            #logger.debug(f"st.session_state['index']: {st.session_state['index']}")
            
            user_input = st.chat_input("Enter your query:")

            # Display chat messages
            chat_container = st.container()
            with chat_container:
                for message in st.session_state['history']:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

            if user_input:
                with st.chat_message("user"):
                    st.markdown(user_input)
                st.session_state['history'].append({"role": "user", "content": user_input})
                logger.info("user input appended")
                
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    full_response = ""
                    conversation_history = "\n".join(
                        [f"{entry['role'].capitalize()}: {entry['content']}" for entry in st.session_state['history']]
                        )
                    query_with_context = f"{conversation_history}\nUser: {user_input}"
                    
                    response = query_engine.query(query_with_context)
                    logger.debug(f"received response이건 repr(response): {repr(response)}")

                    for token in response.response_gen:
                        full_response += token
                        message_placeholder.markdown(full_response + "▌")
                    logger.debug(f"Full_Response: {full_response}")
                    message_placeholder.markdown(full_response)
                st.session_state['history'].append({"role": "assistant", "content": full_response})
                logger.debug(f"Session History: {st.session_state['history']}")
                
            if st.button("Submit"):
                with st.spinner("Saving the exam..."):
                    print(f"컨버세이션 히스토리: {st.session_state['history']}")
                    table_name = collect_student_answers(st.session_state.org_exam_name[1],conversation_history=st.session_state['history'])
                    data = get_data_from_db(f'SELECT * FROM {table_name}')
                    st.dataframe(data)
                    st.success("Exam Saved")
                
                    

            # Add a clear button
            if st.button("Clear Chat"):
                st.session_state['history'] = []
                #st.rerun() #얘는 이걸 왜 넣은 거야?
                
                #이런 걸 넣어서 이때 table을 생성하자
                # with st.spinner("Processing files..."):
                #     documents = load_multimodal_data(uploaded_files)
                #     logger.debug(f"multimodal data READ: {documents}")
                #     st.session_state['index'] = create_index(documents)
                #     logger.debug(f"index CREATED: {st.session_state['index']}")
                #     st.session_state['history'] = []
                #     st.success("Files processed and index created!")    

if __name__ == "__main__":
    main()
