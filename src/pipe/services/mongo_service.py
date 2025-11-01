import os
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient
from pymongo.collection import Collection


_client: Optional[MongoClient] = None


def _get_collection(collection_name: str) -> Collection:
    global _client
    if _client is None:
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
    db_name = os.getenv("MONGODB_DB", "ai_automation")
    return _client[db_name][collection_name]


def fetch_from_mongo(collection: str, query: Optional[Dict[str, Any]] = None, sort: Optional[List[Tuple[str, int]]] = None):
    col = _get_collection(collection)
    cursor = col.find(query or {})
    if sort:
        cursor = cursor.sort(sort)
    return list(cursor)


def insert_into_mongo(collection: str, document: Dict[str, Any]):
    col = _get_collection(collection)
    result = col.insert_one(document)
    return {"inserted_id": str(result.inserted_id)}


def update_in_mongo(collection: str, match: Dict[str, Any], update: Dict[str, Any]):
    col = _get_collection(collection)
    result = col.update_many(match, update)
    return {"matched_count": result.matched_count, "modified_count": result.modified_count}


