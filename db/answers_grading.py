from datetime import datetime
import os
import requests
from sqlalchemy import text
from sqlalchemy import (
    MetaData,
    select,
)
from loguru import logger

from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.llms.nvidia import NVIDIA
from .instr import engine, get_last_instructor_info

NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')


def collect_student_answers(student_exam_sheet, conversation_history):
    metadata_obj = MetaData()

    metadata_obj.create_all(engine)

    sql_database = SQLDatabase(engine, include_tables=[student_exam_sheet])
    print(f"sql database in answers_grading: {sql_database}")

    sql_llm = NVIDIA(  # model="nvidia/llama-3.1-nemotron-51b-instruct",
        # model="nvidia/nemotron-4-340b-instruct",
        model="meta/llama-3.1-405b-instruct",  # too slow
        # model="meta/llama-3.1-70b-instruct",
        # #nvidia/llama-3.1-nemotron-51b-instruct 
        system_prompt="You are a SQL and SQLite expert. Only answer SQL query. Do Not be verbose",
        temperature=0.2,
        api_key=NVIDIA_API_KEY,
        # base_url="https://integrate.api.nvidia.com/v1"
        context_window=128000,
        max_tokens=2048)

    query_engine = NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=[student_exam_sheet],
        llm=sql_llm
    )

    prompt = f"""I will give you a conversation. You should generate an SQL statement and execute UPDATE into the table for the following instruction:
    - There is a table named "{student_exam_sheet}" ,
         where the columns are 'id', 'question_number', 'questions', 'correct_answers', 'style', 'student_answers', 'grading1', and 'grading2'. You need to insert and fill 'student_answers' column based on the conversation.
    - 'id', 'question_number', 'questions', and 'correct_answers' columns are already filled. You only need to insert and fill 'student_answers' column into the corresponding row.
    - In the conversation, you can read [user]'s response mentioning the answer with the 'question_number' or 'questions'. Based on that you need to find the correct row.
    - There are many questions. You should repeat updating the table.
    - The table name should always be double quoted in your generated statement, like this "{student_exam_sheet}"

    The example is:
    UPDATE "Nvidia_Training_exam_Song SET" student_answers = 'United States' WHERE questions LIKE '%%' or
    UPDATE "Nvidia_Training_exam_Song SET" student_answers = 'United States' WHERE question_number = '2' or
    'UPDATE "your_table"
     SET column_name = CASE
     WHEN condition_column = 'value1' THEN 'new_value1'
     WHEN condition_column = 'value2' THEN 'new_value2'
     WHEN condition_column = 'value3' THEN 'new_value3'
     END'
    
    Don't forget use a single quote for a long sentence. When you meet ' (single quote) in a sentence, you MUST escape with '' (two single quotes)

    This is the actual conversation you should work on:
    {conversation_history}

    In any case, you MUST execute your INSERT statement. After executing your query statement, show me your SQL statement. Don't be verbose.
    """

    response = query_engine.query(prompt)
    sql_query = response.response
    print(f'query created from answers_grading: {sql_query} ')

    sql_select = select(text(f"id, questions, student_answers, correct_answers FROM '{student_exam_sheet}'"))

    with engine.begin() as connection:
        result = connection.execute(sql_select)
        records = result.fetchall()
        print(f'records in answers_grading: {records}') 
        
        invoke_url = "https://ai.api.nvidia.com/v1/retrieval/nvidia/nv-rerankqa-mistral-4b-v3/reranking"

        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Accept": "application/json",
        }

        session = requests.Session()
        
        for id, query_text, passage_text1, passage_text2 in records:
            payload = {
                "model": "nvidia/nv-rerankqa-mistral-4b-v3",
                "query": {"text": query_text},
                "passages": [{"text": passage_text1}, {"text": passage_text2}],
            }
            
            if not passage_text1:
                continue
                
            print(f'payload in reranking model: {payload}')
            response = session.post(invoke_url, headers=headers, json=payload)

            response.raise_for_status()
            response_body = response.json()
            print(f'call reranking model: {response_body}')
            rankings = response_body.get('rankings', [])
            #logit = rankings[0].get('logit', None)
            
            for ranking in rankings:
                if ranking['index'] == 0:  # Index 0 corresponds to passage_text1
                    student_answer_logit = ranking.get('logit')
                    print(f'student answer logit:{student_answer_logit}')
                elif ranking['index'] == 1:  # Index 1 corresponds to passage_text2
                    correct_answer_logit = ranking.get('logit')
                    print(f'correct answer logit:{correct_answer_logit}')

            # If logit value exists, update the grade1 column
            if student_answer_logit is not None:
                update_query = text(f"""
                    UPDATE '{student_exam_sheet}'
                    SET grading1 = :student_answer_logit,
                        grading2 = :correct_answer_logit
                    WHERE id = :id
                """)
                
                connection.execute(
                    update_query, {
                        "student_answer_logit": student_answer_logit,
                        "correct_answer_logit": correct_answer_logit,
                        "id": id})

                print(f"Updated id {id} with grading1 = {student_answer_logit} and grading2={correct_answer_logit}")

    return student_exam_sheet


if __name__ == "__main__":
    collect_student_answers(a, b)
