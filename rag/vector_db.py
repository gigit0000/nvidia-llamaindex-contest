from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.milvus import MilvusVectorStore

import os
import logging
from loguru import logger


def vector_db_indexing(documents):
    """Indexing documents to Vector DB"""
    vector_store = MilvusVectorStore(
            host = "127.0.0.1",
            port = 19530,
            dim = 4096  # Update to 4096
        )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    logger.debug("ready to return vector DB index")
    return VectorStoreIndex.from_documents(
        documents, storage_context=storage_context)
   
if __name__=="__main__":
    documents = "Vetorize and save"
    vector_db_indexing(documents)
       
