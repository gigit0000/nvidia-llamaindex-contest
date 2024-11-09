import os
from sqlalchemy import text
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    insert,
    select,
    DateTime,
    CheckConstraint
)
from datetime import datetime
from loguru import logger

from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.llms.nvidia import NVIDIA
from .instr import engine, get_last_instructor_info

NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')

def insert_questions(conversation_history):
    '''insert questions from conversation to db'''
    #engine = create_engine("sqlite:///sql_instr.db", echo=True)
    metadata_obj = MetaData()

    # create instructors SQL table
    names = get_last_instructor_info()
    
    table_name = f"{names['organization']}_{names['exam_name']}" 
    table_name = "-".join(table_name.split())
    print(f'table name: {table_name}')
    
    instructor_table = Table(
        table_name,
        metadata_obj,
        Column('id', Integer, primary_key=True, autoincrement=True),
        #Column('num_questions', String, nullable=False),
        Column('style', String, 
               CheckConstraint(
                   "style IN ('multiple_choice', 'short_phrase', 'essay')"),
                nullable=False),
        Column('difficulty', String, 
               CheckConstraint("difficulty IN ('easy', 'medium', 'hard')"), nullable=False),
        Column('hint', String,
               CheckConstraint("hint IN ('no_hint', 'broad', 'specific')"),
                nullable=False),
        Column('questions', String, nullable=False),
        Column('answers', String, nullable=False),
        Column('date_created', DateTime, default=datetime.now())
        
    )
    metadata_obj.create_all(engine)

    sql_database = SQLDatabase(engine, include_tables=["instructors"])
    #print(f"sql database: {sql_database}")
    
    #initialize llm and llamaindex engine
    sql_llm = NVIDIA(  # model="nvidia/llama-3.1-nemotron-51b-instruct",
        # model="nvidia/nemotron-4-340b-instruct",
        model="meta/llama-3.1-405b-instruct",  
        # model="meta/llama-3.1-70b-instruct",
        # #nvidia/llama-3.1-nemotron-51b-instruct 이건 preview
        system_prompt="You are a SQL and SQLite expert. Only answer SQL query. Do Not be verbose",
        temperature=0.2,
        api_key=NVIDIA_API_KEY,
        # base_url="https://integrate.api.nvidia.com/v1"
        context_window=128000,
        max_tokens=2048)

    query_engine = NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=[table_name],
        llm=sql_llm
    )

    prompt = f"""I will give you a conversation. You should generate an SQL INSERT statement and execute INSERT into the table for the following instruction: 
    - There is a table named "{table_name}
        " where the columns are 'style', 'difficulty', 'hint', 'questions', and 'answers'. You need to insert each row based on the conversation.
    - 'style' column only can have 'multiple_choice', 'short_phrase', or 'essay'
    - 'difficulty' column only can have 'easy', 'medium', 'hard'
    - 'hint' column only can have 'no_hint', 'broad' or 'specific'
    -  When the 'style' is 'multiple_choice', you MUST include all the options in 'questions' for the question
    -  When you meet ' (single quote) in 'questions' or 'answers', you MUST escape with '' (two single quotes) 
    - The table name should always be double quoted in your generated statement, like this "{table_name}"
    
    This is an example:
    --------------------------
    Conversation: 
    [user]I want 2 questions in the exam. Both are about cities. The answer style should be short phrase and make them easy. You can give a broad hint.
    [bot] I see. Which city is known as "The Big Apple" and serves as the most populous city in the United States?
Answer: New York City
What ancient Italian city was buried under volcanic ash when Mount Vesuvius erupted in 79 CE?
Answer: Pompeii
    Do you like these questions?
    [user] Looks good. Thanks! 
    -------------------------
    
    This is the actual conversation you should work on:
    {conversation_history}
    
    In any case, you MUST execute your INSERT statement. After executing INSERT, show me your SQL statement. Don't be verbose.
    """

    # Get the SQL query from the LLM
    response = query_engine.query(prompt)
    sql_query = response.response
    print(f'query from llm: {sql_query}')
    
    # Manual insert just in case
    # Execute the generated SQL query
    # with engine.connect() as connection:
    #     print(f'인서트 실행 전')
    #     result = connection.execute(text(sql_query))
    #     print(f'인서트 실행 후')
    #     connection.commit()

    return table_name



if __name__ == "__main__":
    insert_questions("where is seoul")
