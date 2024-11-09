import os
import sys
import streamlit as st
import sqlite3
import pandas as pd
from PIL import Image
import logging
from loguru import logger

from agents.agent_sage import exam_sage_settings
from db.instr import insert_instr, get_exam_info, get_last_instructor_info
from db.questions import insert_questions
from rag.vector_db import vector_db_indexing
from rag.document_processors import load_multimodal_data, load_data_from_directory

logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True)
logger.add("Mymy_log.log", format="{time} | {level} | {message}", level="INFO")

NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')
db_table = "instructors"

# Set up the page configuration
st.set_page_config(
    layout="wide",
    menu_items={
        "Get help": "https://github.com/gigit0000/nvidia-llamaindex-contest",
        "Report a bug": "https://github.com/gigit0000/nvidia-llamaindex-contest",
        "About": """
        Developed by William Song\n
        For NVIDIA Contest\n
        Powered by NVIDIA and LlamaIndex 
        """,
    },
)

@st.cache_resource
def create_index(_documents):
    """Create a vector store index from documents."""
    return vector_db_indexing(_documents)

@st.cache_resource
def initialize_agent_settings(instructor_name):
    exam_sage_settings(instructor_name)

@st.cache_resource
def get_exam_name():
    return get_last_instructor_info()

@st.cache_data
def get_data_from_db(query):
    try: 
        conn = sqlite3.connect("examsage.db")
        df = pd.read_sql_query(query, conn)
        df = df.rename(columns={"id": "No", "style": "Type", "difficulty": "Difficulty", "hint": "Hint", "questions": "Questions", "answers": "Answers", "date_created": "Created at"})
        conn.close()
    except Exception as e:
        print(f'question table pandas display: {e}')    
    return df

# Main function to run the Streamlit app
def main():

    logger.debug("Streamlit re-start")

    # Navigation control between pages
    if "page" not in st.session_state:
        st.session_state.page = "input_form"

    # Page 1: User Input Form
    if st.session_state.page == "input_form":
        
        st.title("Welcome to Exam Sage!")
        st.markdown("I'll **prepare your exam questions** in any way you like. Using your materials, like lecture notes, slides, PDFs, charts, or anything else, along with my knowledge base, I can create multiple-choice, short-phrase or essay questions with you.")
        st.markdown("That’s not all! I’ll act as a TA during the exams and **give hints** if you’d like. Plus, I can do **reference grading** for your exam!")
        st.header("Please fill in your information")

        with st.form("user_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            organization = st.text_input("Organization")
            exam_name = st.text_input("Exam Name")  
            st.session_state.organization = organization
            st.session_state.exam_name = exam_name

            # Create a file uploader widget
            uploaded_file = st.file_uploader(
                "Upload your organization’s logo (optional)", type=[
                    "jpg", "jpeg", "png"])

            if uploaded_file is not None:
                # Open and display the uploaded image
                image = Image.open(uploaded_file)
                st.image(
                    image,
                    caption="Uploaded Image",
                    use_column_width=False)

                # Save the uploaded image
                save_path = os.path.join("images", uploaded_file.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())  
                st.session_state.image_path = save_path
                st.success(f"Image saved")
            else:
                st.session_state.image_path="images/exam_sage_image.PNG"                
            
            submit_button = st.form_submit_button("Confirm")

        if submit_button:
            if name and email and organization and exam_name:
                #test phase comment 
                #save_user_info(name, email, organization, exam_name)
                insert_instr(db_table, name, email, organization, exam_name, st.session_state.image_path)


                st.session_state.page = "llm_communication"
                st.success("Information saved! Moving to the next page...")
                st.session_state.exam_info = get_exam_name()
                initialize_agent_settings(st.session_state.exam_info['name'])
                #st.rerun()  #임시로 코멘트 처리
            else:
                st.error("Kindly complete all required fields")
     
    #임시로 막음            
    #if st.session_state.page == "llm_communication":
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(f"## {st.session_state.organization}")
        st.markdown(f"### {st.session_state.exam_name}")
        if 'image_path' in st.session_state:
            image = Image.open(st.session_state.image_path)
            st.image(image, use_column_width=True)
        
        input_method = st.radio("Choose input method:", ("Upload Files", "Enter Directory Path"))
        
        if input_method == "Upload Files":
            uploaded_files = st.file_uploader("Drag and drop files here", accept_multiple_files=True)
            if uploaded_files and st.button("Process Files"):
                with st.spinner("Processing files..."):
                    documents = load_multimodal_data(uploaded_files)
                    logger.debug(f"multimodal data READ: {documents}")
                    st.session_state['index'] = create_index(documents)
                    logger.debug(f"index CREATED: {st.session_state['index']}")
                    st.session_state['history'] = []
                    st.success("Files processed and index created!")
        else:
            directory_path = st.text_input("Enter directory path:")
            if directory_path and st.button("Process Directory"):
                if os.path.isdir(directory_path):
                    with st.spinner("Processing directory..."):
                        documents = load_data_from_directory(directory_path)
                        st.session_state['index'] = create_index(documents)
                        st.session_state['history'] = []
                        st.success("Directory processed and index created!")
                else:
                    st.error("Invalid directory path. Please enter a valid path.")
    
    with col2:
        st.markdown("")
        st.markdown("""
                    ### Turn your documents into smart questions!
                    First, upload your documents to the left pane. Next, let's discuss the types of questions you'd like and the preferred answer formats. As we chat, Exam Sage will create questions and answers tailored to your needs.
                    
                    Ready? Let's get started!
                    Everything is done, please click **"Finalize"** button to save the exam.
                    """)
        if 'index' in st.session_state:
            st.markdown("### Chat")
            if 'history' not in st.session_state:
                st.session_state['history'] = []
            
            query_engine = st.session_state['index'].as_query_engine(similarity_top_k=20, streaming=True)
            logger.debug("as_query_engine CALLED")
            
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
                
            if st.button("Finalize"):
                with st.spinner("Saving the exam..."):
                    table_name = insert_questions(conversation_history=st.session_state['history'])
                    data = get_data_from_db(f'SELECT * FROM "{table_name}"')
                    st.dataframe(data)
                    st.success("Exam Saved")

            # Add a clear button
            if st.button("Clear Chat"):
                st.session_state['history'] = []
                #st.rerun() #얘는 이걸 왜 넣은 거야?
                 
                 
if __name__ == "__main__":
    main()
