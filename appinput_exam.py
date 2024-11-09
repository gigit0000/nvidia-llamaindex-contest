import os
import sys
import streamlit as st
from PIL import Image
import sqlite3
import pandas as pd
import logging
from loguru import logger

from llama_index.core import Settings, Document, ListIndex

from db.instr import student_insert_query
from db.exam_helper import get_org_exam_name_info, db_engine_initialize
from db.questions import insert_questions
from db.answers_grading import collect_student_answers
from agents.agent_sage import exam_sage_settings
from agents.agent_sage_student import exam_sage_student_settings
from rag.vector_db import vector_db_indexing

logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True)
logger.add("Mymy_log.log", format="{time} | {level} | {message}", level="INFO")

db_table = "students" 

NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')

# Set up the page configuration
st.set_page_config(
    layout="wide",
    menu_items={
        "Get help": "https://github.com/gigit0000/nvidia-llamaindex-contest",
        "Report a bug": "https://github.com/gigit0000/nvidia-llamaindex-contest",
        "About": """
        Exam Taker Screen on Exam Sage\n
        Developed by William Song\n
        For NVIDIA Contest\n
        Powered by NVIDIA and LlamaIndex 
        """,
    },
)



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


def main():
    if "page" not in st.session_state:
        st.session_state.page = "input_form"
        
    if "org_exam_name" not in st.session_state:
        st.session_state["org_exam_name"] = None

    # Page 1: User Input Form
    if st.session_state.page == "input_form":
        
        st.title("The exam is ready!")
        st.markdown(
            "Welcome to Exam Sage for you exam. I'm your exam assistant. Ask away, and I'll give you tailored feedback.")
        st.markdown(
            "Enter your information below. If you're ready, please click the button to start the exam.")

        with st.form("user_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")  
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
                                
                try:
                    st.session_state.org_exam_name = get_org_exam_name(name,organization, exam_name)
                    if st.session_state.org_exam_name[0] == 'Invalid':
                        st.error("Kindly fill correct organization and exam name")
                  
                    initialize_agent_settings(name, st.session_state.org_exam_name[0]) 
                    st.success("Information saved! Moving to the next page...")  
                    st.session_state.page = "llm_communication"
                    st.rerun()
                except:
                    st.error("Kindly fill correct organization and exam name")        
            else:
                st.error("Kindly complete all required fields")
        
            
          
    if st.session_state.page == "llm_communication":
        col1, col2 = st.columns([1, 1])
        
        with col1:

            if 'image_path' in st.session_state:
                image = Image.open(st.session_state.image_path)
                st.image(image, use_column_width=True)

            if 'org_exam_name' not in st.session_state or st.session_state.org_exam_name is None:
                st.session_state.org_exam_name = [""]

            st.title(st.session_state.org_exam_name[0].replace("_", " ").title())
           
            data = get_data_from_db(f'SELECT id, questions FROM "{st.session_state.org_exam_name[0]}"')
            st.dataframe(data)

            # df = show_questions()
            # st.dataframe(df)
            st.session_state.next_col = True
                    
        with col2:
            st.markdown("""
                        ### Now, the exam has started.
                        Read your questions carefully and enter your answers here.
                        I can help answer your questions and provide hints for the ones your instructor has allowed. You can also feel free to ask me for additional information, just be sure to include the question number. However, you are not allowed to ask me for the answers.
                        
                        Everything is done, please click **"Submit"** button. Then the grading will be started!
                        """)
            if st.session_state.next_col:
                st.header("Chat")
                if 'history' not in st.session_state:
                    st.session_state['history'] = []
                
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
                        print(f"conversation history: {st.session_state['history']}")
                        table_name = collect_student_answers(st.session_state.org_exam_name[1],conversation_history=st.session_state['history'])
                        print(f'table name check: {table_name}')
                        data = get_data_from_db(f'SELECT * FROM "{table_name}"')
                        st.dataframe(data)
                        st.success("Exam Saved")
                    

if __name__ == "__main__":
    main()
