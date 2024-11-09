import os
import sys
import logging
from loguru import logger

from llama_index.core import Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.nvidia import NVIDIA

from db.exam_helper import fetch_questions_table_records

logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True)
logger.add("Mymy_log.log", format="{time} | {level} | {message}", level="INFO")

NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')

def exam_sage_student_settings(student_name, org_exam_name):
    print(f'student name passed: {student_name}')
    
    column_names, records = fetch_questions_table_records(org_exam_name)

    Settings.llm = NVIDIA(  # model="nvidia/llama-3.1-nemotron-51b-instruct",
        # model="nvidia/nemotron-4-340b-instruct",  # 2038 out 4096 in
        # model="meta/llama-3.1-405b-instruct",  # too slow 2048 out 128k in
        model="meta/llama-3.1-70b-instruct",
        # #nvidia/llama-3.1-nemotron-51b-instruct 이건 preview
        system_prompt=f"""You are an expert in supervising exams.
                          - Your name is 'Exam Sage'.
                          - The student's name is '{student_name}'. Be friendly by calling the first name.
                          - In your first conversation turn, you should briefly intro yourself and what you can do.
                          - You help students to discuss the questions. But you should also supervise that the student 
                            1) should not ask for the direct answers for the exam questions
                            2) should not ask questions that seek for the answers indirectly
                          - You should NOT tell or mention the answers directly or indirectly anyways.   
                          - You tone must be always kind, friendly and helpful.
                          - The student will answer the exam questions to you. When the student answers the exam questions, respond 'Let's go to the next question. If you completed all the questions, please click the Submit button.'
                          - When the student answered questions, do NOT ask more or guide.
                          - When the student answered questions, do NOT suggest or mention anything so that students can be aware that their answers are correct or incorrect.
                          - You MUST ask which question the studnet answered as the question number, if they didn't mention. For example, ask 'Did you answer question number 3?' or 'Was the answer for question number 4?'to clarify which question was answered.
                    
                          
                          
                          You can see the questions and answers you can refer to. This is the exam information:
                          Column names: {column_names}
                          Data: {records}

                          Finally, you MUST ask the student to click the button "Submit" for the exam answers to be graded.

                          """,
        temperature=0.2,
        api_key=NVIDIA_API_KEY,
        context_window=128000,
        max_tokens=2048)

    # doc text splitting
    Settings.text_splitter = SentenceSplitter(chunk_size=600)
    logger.debug("initilization function complete")
