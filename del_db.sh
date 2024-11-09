#!/bin/bash

# Remove the lock file and the database file
rm .milvus_llamaindex.db.lock
rm milvus_llamaindex.db
rm -r ./vectorstore

echo " milvus db and vectorstore file removed."
