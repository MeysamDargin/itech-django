"""
MongoDB Utility Functions for the itech project.
This module provides helper functions to interact with MongoDB.
"""

import pymongo
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# یک نمونه MongoClient گلوبال برای استفاده مجدد
_mongo_client = None

def get_mongo_client():
    """
    Returns a MongoDB client instance connected to the MongoDB server.
    Uses a global client instance for connection pooling.
    
    Returns:
        pymongo.MongoClient: A MongoDB client instance.
    """
    global _mongo_client
    
    if _mongo_client is not None:
        return _mongo_client
        
    try:
        # Connect directly to MongoDB without replica set configuration
        _mongo_client = pymongo.MongoClient(settings.MONGODB_URI, directConnection=True)
        # Test the connection
        _mongo_client.admin.command('ping')
        logger.info("Connected to MongoDB server successfully")
        return _mongo_client
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {str(e)}")
        raise

def get_database(db_name=None):
    """
    Returns a MongoDB database instance.
    
    Args:
        db_name (str, optional): The name of the database to get. If not provided,
                                 the database name from the MongoDB URI is used.
    
    Returns:
        pymongo.database.Database: A MongoDB database instance.
    """
    client = get_mongo_client()
    
    if db_name is None:
        # Extract database name from the MongoDB URI
        uri_parts = settings.MONGODB_URI.split('/')
        if len(uri_parts) > 3:
            db_name = uri_parts[3].split('?')[0]  # Remove query parameters if present
        else:
            db_name = 'itech'  # Default database name
    
    return client[db_name]

def get_collection(collection_name, db_name=None):
    """
    Returns a MongoDB collection instance.
    
    Args:
        collection_name (str): The name of the collection to get.
        db_name (str, optional): The name of the database containing the collection.
                                 If not provided, the database from the URI is used.
    
    Returns:
        pymongo.collection.Collection: A MongoDB collection instance.
    """
    db = get_database(db_name)
    return db[collection_name]

def insert_document(collection_name, document, db_name=None):
    """
    Inserts a document into a MongoDB collection.
    
    Args:
        collection_name (str): The name of the collection to insert into.
        document (dict): The document to insert.
        db_name (str, optional): The name of the database containing the collection.
        
    Returns:
        str: The ID of the inserted document.
    """
    collection = get_collection(collection_name, db_name)
    result = collection.insert_one(document)
    return str(result.inserted_id)

def find_documents(collection_name, query=None, projection=None, db_name=None):
    """
    Finds documents in a MongoDB collection.
    
    Args:
        collection_name (str): The name of the collection to search.
        query (dict, optional): The query to filter documents. If None, returns all documents.
        projection (dict, optional): The fields to include or exclude in the results.
        db_name (str, optional): The name of the database containing the collection.
        
    Returns:
        list: A list of matching documents.
    """
    collection = get_collection(collection_name, db_name)
    cursor = collection.find(query or {}, projection or {})
    return list(cursor)

def update_document(collection_name, query, update, db_name=None):
    """
    Updates a document in a MongoDB collection.
    
    Args:
        collection_name (str): The name of the collection containing the document.
        query (dict): The query to find the document to update.
        update (dict): The update operations to apply to the document.
        db_name (str, optional): The name of the database containing the collection.
        
    Returns:
        int: The number of documents modified.
    """
    collection = get_collection(collection_name, db_name)
    result = collection.update_one(query, update)
    return result.modified_count

def delete_document(collection_name, query, db_name=None):
    """
    Deletes a document from a MongoDB collection.
    
    Args:
        collection_name (str): The name of the collection containing the document.
        query (dict): The query to find the document to delete.
        db_name (str, optional): The name of the database containing the collection.
        
    Returns:
        int: The number of documents deleted.
    """
    collection = get_collection(collection_name, db_name)
    result = collection.delete_one(query)
    return result.deleted_count

# تابع برای بستن اتصال در زمان خاموش شدن سرور
def close_mongo_connection():
    """Close the MongoDB connection when the server shuts down."""
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
        logger.info("MongoDB connection closed") 