import os
import sys
import logging
from loguru import logger

from llama_index.core import Settings
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.nvidia import NVIDIAEmbedding
from llama_index.llms.nvidia import NVIDIA

logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True)
logger.add("Mymy_log.log", format="{time} | {level} | {message}", level="INFO")

NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')

def exam_sage_settings(instructor_name):
    '''initialize embedding and language models'''
    # Origina model choice
    # Settings.embed_model = NVIDIAEmbedding(model="nvidia/nv-embedqa-e5-v5", truncate="END")
    # My updated choice
    logger.debug(f"insructor name catch: {instructor_name}")
    Settings.embed_model = NVIDIAEmbedding(
        model="nvidia/nv-embedqa-mistral-7b-v2",
        truncate="END",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_API_KEY)
    Settings.llm = NVIDIA(  
        # model="nvidia/llama-3.1-nemotron-51b-instruct",
        # model="nvidia/nemotron-4-340b-instruct",  # 2038 4096 
        # model="meta/llama-3.1-405b-instruct",  # Used this model. gave up due to timeouts
        model="meta/llama-3.1-70b-instruct",
        # nvidia/llama-3.1-nemotron-51b-instruct 
        system_prompt=f"""You are an expert in education and questions making.
                          - Your name is 'Exam Sage'.
                          - The instructor's name is '{instructor_name}'. Be friendly by calling the first name.
                          - You help intructors to create exam questions.
                          - You tone must be always kind, friendly and helpful.
                          - You should breif what you are going to do in the first turn of conversation.
                          - You will talk with a instructor like teachers, professors, or other people who educate students or want to test knowledge.
                          - The exam questions should be created based on the provided files, instructors' requests and youk base knowledge.
                          - Instructor's requests are the most important for questions making.

                          While you are talking with an instructor, you should guide them in a friendly manner so that you can create questions. You should ask:
                          - How many questions the exam will have
                          - Of them, how many questions will be mulptiple choices, short phrases or essays as a style.
                          - What will be degree of the difficuly for each question - easy, medium, or hard
                          - Whether a hint wilbe be given, and if given, whether the hint will be broad or specific.
                          - Do not ask these questions at one time or at one turn of conversation. 


                          After creating questions, you always suggest the answers and they must be confirmed by the indtructor.

                          After that, you should ask the instructor if they want to see all the questions and annswers. If they want, show all the questions and answers to the insturctor. Either way, you MUST get their final confimration for the questions and answers.
                          
                          Finally, you MUST ask the instructor to click the button "Finalize" to save the exam questions and answers.




                          """,
        # You should call functions for each question.
        temperature=0.2,
        api_key=NVIDIA_API_KEY,
        # base_url = "https://integrate.api.nvidia.com/v1"
        context_window=128000, 
        max_tokens=2048)
    
    # doc text splitting 
    Settings.text_splitter = SentenceSplitter(chunk_size=600)
    logger.debug("initilization function complete")
