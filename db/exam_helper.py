import os
from datetime import datetime
from sqlalchemy import text
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    select,
    DateTime,
)
from loguru import logger

from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.llms.nvidia import NVIDIA
from .instr import engine, get_last_instructor_info


NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')

sql_database = None
exam_llm = None
metadata_obj = None


def fetch_questions_table_records(org_exam_name):

    sql_select = select(text(f"* FROM '{org_exam_name}'"))

    with engine.begin() as connection:
        result = connection.execute(sql_select)
        records = result.fetchall()
        column_names = result.keys()
        print(f'column names: {column_names}')
    return column_names, records

def db_engine_initialize():
    engine = create_engine("sqlite:///examsage.db", echo=True)
    
    global metadata_obj
    metadata_obj = MetaData()

    global sql_database
    sql_database = SQLDatabase(engine)
    print(f"sql db engine initialization: {sql_database}")

    global exam_llm
    exam_llm = NVIDIA(  # model="nvidia/llama-3.1-nemotron-51b-instruct",
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


def get_org_exam_name_info(name, organization, exam_name):

    print(f'before query')
    query_engine = NLSQLTableQueryEngine(
        sql_database=sql_database,
        #tables=[table_name],
        llm=exam_llm
    )
    print(f'after query')
    prompt = f"""I will give you an organization name and an exam_name. For instance, organization is World University and exam_name is final exam. There is a table name in this database simliar to those. For example, the table name will be 'world-university_final-exam' for the above case. You should return the table name when organization and exam_name is given. To find the matching table name, use %. 
    
    Here is the organization and exam_name:
    - organization: {organization}
    - exam_name: {exam_name} 

    Don't be verbose. Just return the table name. If you cannot find one, return 'Invalid'
    

    """

    response = query_engine.query(prompt)
    returned_table_name = response.response
    print(f'table name returned: {returned_table_name} ')
    
    if returned_table_name != 'Invalid':
        student_exam_sheet_table_name = '_'.join([returned_table_name, name])
        print(f'student exam sheet: {student_exam_sheet_table_name}')
        student_exam_sheet_table = Table(
        student_exam_sheet_table_name,
        metadata_obj,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('question_number', String, nullable=False),
        Column('questions', String, nullable=False),
        Column('correct_answers', String, nullable=False),
        Column('style', String, nullable=False),
        Column('student_answers', String, nullable=True),
        Column('grading1', String, nullable=False),
        Column('grading2', String, nullable=False),
        Column('date_created', DateTime, default=datetime.now())
        )
        metadata_obj.create_all(engine)
        
        with engine.connect() as connection:
            table_obj = Table(returned_table_name, metadata_obj, autoload_with=engine)
            select_stmt = select(text('id, questions, answers, style')).select_from(table_obj)
            result = connection.execute(select_stmt)
            source_data = result.fetchall()
        
            # Prepare data for insertion
            insert_data = []
            for row in source_data:
                insert_data.append({
                    'question_number': str(row.id),  # Convert id to string as per schema
                    'questions': row.questions,
                    'correct_answers': row.answers,
                    'style': row.style,
                    'student_answers': "",
                    'grading1': "",  # Default value
                    'grading2': "",  # Default value
                    'date_created': datetime.now()
                })
            
            # Insert data into new table
            if insert_data:
                insert_stmt = student_exam_sheet_table.insert().values(insert_data)
                connection.execute(insert_stmt)
                connection.commit()
        
        
    return [returned_table_name, student_exam_sheet_table_name]


if __name__ == "__main__":
    insert_questions("where is seoul")
