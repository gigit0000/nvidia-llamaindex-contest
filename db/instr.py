from llama_index.core import SQLDatabase
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    insert,
    select,
    desc,
    DateTime
)
from sqlalchemy import text
from datetime import datetime

from loguru import logger

engine = create_engine("sqlite:///examsage.db", echo=True)  #for module questions.py

def get_exam_info():
    pass

def get_last_instructor_info():
    """Fetch the last entry's name, organization, and exam_name from the instructors table."""
    metadata_obj = MetaData()
    instructor_table = Table('instructors', metadata_obj, autoload_with=engine)

    with engine.connect() as conn:
        # Query to select the last entry's specific columns
        query = select(
            instructor_table.c.name,
            instructor_table.c.organization,
            instructor_table.c.exam_name
        ).order_by(desc(instructor_table.c.id)).limit(1)

        result = conn.execute(query).fetchone()

        # Convert result to a dictionary if found
        if result:
            return {
                'name': result.name,
                'organization': result.organization,
                'exam_name': result.exam_name
            }
        else:
            return None

def insert_instr(db_table, name, email, detail1, detail2, detail3):
    '''insert instructor information'''
    metadata_obj = MetaData()

    # create instructors and studnets SQL table      
    if db_table == "instructors": 
        table_name = db_table
        instructor_table = Table(
            table_name,
            metadata_obj,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('name', String, nullable=False),
            Column('email', String, nullable=False),
            Column('organization', String, nullable=False),   
            Column('exam_name', String, nullable=False),      
            Column('image_path', String, nullable=True),
            Column('date_created', DateTime, default=datetime.now())
        )
        metadata_obj.create_all(engine)

        #rows = [{"name": "Seoul", "email": "df@df.com",
        #         "organization": "Korea", "exam_name": "midterm"}, ]
        
        instructor_data = {
            'name': name,
            'email': email,
            'organization': detail1,
            'exam_name': detail2,
            'image_path': detail3
        }
        
        sql_insert = insert(instructor_table).values(**instructor_data)
        with engine.begin() as connection:
            connection.execute(sql_insert)

        # view current table
        sql_select = select(
            instructor_table.c.id,
            instructor_table.c.name,
            instructor_table.c.email,
            instructor_table.c.organization,
            instructor_table.c.exam_name,
            instructor_table.c.image_path,
            instructor_table.c.date_created  
        ).select_from(instructor_table)

        with engine.connect() as connection:
            results = connection.execute(sql_select).fetchall()
            print(results)
            logger.debug(f"Insert result: {results}")
     
    if db_table == "students":
        table_name = db_table
        student_table = Table(
            table_name,
            metadata_obj,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('name', String, nullable=False),
            Column('email', String, nullable=False),
            Column('student_id', String, nullable=False),
            Column('registration_id', String, nullable=False),
            Column('date_created', DateTime, default=datetime.now())
        )
        metadata_obj.create_all(engine)

        # rows = [{"name": "Seoul", "email": "df@df.com",
        #         "student_id": "Korea", "registration_id": "midterm"}, ]

        student_data = {
            'name': name,
            'email': email,
            'student_id': detail1,
            'registration_id': detail2
        }

        sql_insert = insert(student_table).values(**student_data)
        with engine.begin() as connection:
            connection.execute(sql_insert)

        # view current table
        sql_insert = select(
            student_table.c.id,
            student_table.c.name,
            student_table.c.email,
            student_table.c.student_id,
            student_table.c.registration_id,
            student_table.c.date_created
        ).select_from(student_table)

        with engine.connect() as connection:
            results = connection.execute(sql_insert).fetchall()
            print(results)
            logger.debug(f"Insert result: {results}")

def student_insert_query(db_table, name, email, organization, exam_name, student_id):
    '''insert students info'''
    metadata_obj = MetaData()

    # create instructors and studnets SQL table

    if db_table == "instructors":
        table_name = db_table
        instructor_table = Table(
            table_name,
            metadata_obj,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('name', String, nullable=False),
            Column('email', String, nullable=False),
            Column('organization', String, nullable=False),
            Column('exam_name', String, nullable=False),
            Column('student_id', String, nullable=True),
            Column('date_created', DateTime, default=datetime.now())
        )
        metadata_obj.create_all(engine)

        instructor_data = {
            'name': name,
            'email': email,
            'organization': organization,
            'exam_name': exam_name,
            'student_id': student_id
        }

        sql_insert = insert(instructor_table).values(**instructor_data)
        with engine.begin() as connection:
            connection.execute(sql_insert)

        # view current table
        sql_insert = select(
            instructor_table.c.id,
            instructor_table.c.name,
            instructor_table.c.email,
            instructor_table.c.organization,
            instructor_table.c.exam_name,
            instructor_table.c.student_id,
            instructor_table.c.date_created
        ).select_from(instructor_table)

        with engine.connect() as connection:
            results = connection.execute(sql_insert).fetchall()
            print(results)
            logger.debug(f"Insert result: {results}")

    if db_table == "students":
        table_name = db_table
        student_table = Table(
            table_name,
            metadata_obj,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('name', String, nullable=False),
            Column('email', String, nullable=False),
            Column('student_id', String, nullable=False),
            Column('registration_id', String, nullable=False),
            Column('date_created', DateTime, default=datetime.now())
        )
        metadata_obj.create_all(engine)

        student_data = {
            'name': name,
            'email': email,
            'student_id': organization,
            'registration_id': exam_name
        }

        sql_insert = insert(student_table).values(**student_data)
        with engine.begin() as connection:
            connection.execute(sql_insert)

        # view current table
        sql_insert = select(
            student_table.c.id,
            student_table.c.name,
            student_table.c.email,
            student_table.c.student_id,
            student_table.c.registration_id,
            student_table.c.date_created
        ).select_from(student_table)

        with engine.connect() as connection:
            results = connection.execute(sql_insert).fetchall()
            print(results)
            logger.debug(f"Insert result: {results}")


if __name__ == "__main__":
    insert_instr('instructors','aaa', 'bbb', 'C', 'D', 'e')
    name = get_last_instructor_info()

    

