import logging
import sys
# Force PyMongo to fall back to the standard library ssl module by preventing pyOpenSSL import
sys.modules['OpenSSL'] = None

from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

logger = logging.getLogger("ecopilot.database")

class MockCollection:
    """Fallback mock collection to avoid crashes if MongoDB is not available."""
    def __init__(self, name: str):
        self.name = name
        self._store = []

    def _match_doc(self, doc, filter_dict) -> bool:
        for k, v in filter_dict.items():
            doc_val = doc.get(k)
            if isinstance(v, dict):
                for op, op_val in v.items():
                    if op == "$gte":
                        if doc_val is None or not (doc_val >= op_val):
                            return False
                    elif op == "$lte":
                        if doc_val is None or not (doc_val <= op_val):
                            return False
                    elif op == "$gt":
                        if doc_val is None or not (doc_val > op_val):
                            return False
                    elif op == "$lt":
                        if doc_val is None or not (doc_val < op_val):
                            return False
                    elif op == "$ne":
                        if doc_val == op_val:
                            return False
                    elif op == "$in":
                        if doc_val not in op_val:
                            return False
                    elif op == "$regex":
                        import re
                        options = v.get("$options", "")
                        flags = 0
                        if "i" in options.lower():
                            flags = re.IGNORECASE
                        try:
                            pattern = re.compile(op_val, flags)
                            if not pattern.search(str(doc_val or "")):
                                return False
                        except Exception:
                            return False
                    elif op == "$options":
                        continue
                    else:
                        if doc_val != v:
                            return False
            else:
                if doc_val != v:
                    return False
        return True

    async def find_one(self, filter, *args, **kwargs):
        import copy
        for doc in self._store:
            if self._match_doc(doc, filter):
                return copy.deepcopy(doc)
        return None

    async def insert_one(self, document, *args, **kwargs):
        import copy
        from bson import ObjectId
        if "_id" not in document:
            document["_id"] = ObjectId()
        # Deepcopy to prevent reference mutation bugs
        self._store.append(copy.deepcopy(document))
        class InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id
        return InsertResult(document["_id"])

    def find(self, filter=None, *args, **kwargs):
        filter = filter or {}
        class MockCursor:
            def __init__(self, docs):
                self.docs = docs
                self.index = 0
            def sort(self, key_or_list, direction=None, *args, **kwargs):
                if isinstance(key_or_list, list):
                    if not key_or_list:
                        return self
                    for key, dir_val in reversed(key_or_list):
                        reverse = (dir_val == -1)
                        self.docs.sort(key=lambda x: (x.get(key) is not None, x.get(key)), reverse=reverse)
                else:
                    key = key_or_list
                    reverse = (direction == -1)
                    self.docs.sort(key=lambda x: (x.get(key) is not None, x.get(key)), reverse=reverse)
                return self
            def skip(self, count, *args, **kwargs):
                self.docs = self.docs[count:]
                return self
            def limit(self, count, *args, **kwargs):
                if count is not None:
                    self.docs = self.docs[:count]
                return self
            async def to_list(self, length=None):
                import copy
                if length is not None:
                    return [copy.deepcopy(d) for d in self.docs[:length]]
                return [copy.deepcopy(d) for d in self.docs]
            def __aiter__(self):
                return self
            async def __anext__(self):
                import copy
                if self.index < len(self.docs):
                    res = self.docs[self.index]
                    self.index += 1
                    return copy.deepcopy(res)
                raise StopAsyncIteration
        
        matched_docs = []
        for doc in self._store:
            if self._match_doc(doc, filter):
                matched_docs.append(doc)
        return MockCursor(matched_docs)

    async def update_one(self, filter, update, *args, **kwargs):
        target_doc = None
        for doc in self._store:
            if self._match_doc(doc, filter):
                target_doc = doc
                break

        modified = 0
        if target_doc:
            if "$set" in update:
                target_doc.update(update["$set"])
            if "$push" in update:
                for k, v in update["$push"].items():
                    if k not in target_doc or not isinstance(target_doc[k], list):
                        target_doc[k] = []
                    target_doc[k].append(v)
            modified = 1
        elif kwargs.get("upsert") or (len(args) > 0 and args[0] is True):
            new_doc = {}
            for k, v in filter.items():
                if not isinstance(v, dict) and not k.startswith("$"):
                    new_doc[k] = v
            if "$set" in update:
                new_doc.update(update["$set"])
            from bson import ObjectId
            if "_id" not in new_doc:
                new_doc["_id"] = ObjectId()
            self._store.append(new_doc)
            modified = 1

        class UpdateResult:
            modified_count = modified
        return UpdateResult()

    async def delete_one(self, filter, *args, **kwargs):
        target_doc = None
        for doc in self._store:
            if self._match_doc(doc, filter):
                target_doc = doc
                break

        if target_doc:
            self._store.remove(target_doc)
        class DeleteResult:
            deleted_count = 1 if target_doc else 0
        return DeleteResult()

    async def delete_many(self, filter, *args, **kwargs):
        count = 0
        docs_to_delete = []
        for doc in self._store:
            if self._match_doc(doc, filter):
                docs_to_delete.append(doc)
        for doc in docs_to_delete:
            self._store.remove(doc)
            count += 1
        class DeleteResult:
            deleted_count = count
        return DeleteResult()


class MockDatabase:
    """Fallback mock database mapping collections dynamically."""
    def __init__(self):
        self._collections = {}

    def __getitem__(self, name: str) -> MockCollection:
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]


class DatabaseManager:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    def get_db(cls):
        """Returns the database client instance, falling back to mock if needed."""
        if cls.db is not None:
            return cls.db

        if not settings.mongodb_uri or settings.mongodb_uri == "dummy":
            logger.warning("MongoDB URI is empty or dummy. Starting in-memory Mock DB.")
            cls.db = MockDatabase()
            return cls.db

        try:
            logger.info("Initializing MongoDB Async Client...")
            cls.client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
            # Fetch database name from connection string or default
            db_name = settings.mongodb_uri.split("/")[-1].split("?")[0] or "ecopilot"
            if db_name.endswith("/"):
                db_name = db_name[:-1]
            if not db_name:
                db_name = "ecopilot"
            cls.db = cls.client[db_name]
            return cls.db
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}. Falling back to Mock DB.")
            cls.db = MockDatabase()
            return cls.db


async def get_db():
    """FastAPI Dependency for database access."""
    return DatabaseManager.get_db()


async def init_db_indexes(db):
    """Initializes MongoDB collection indexes asynchronously using Motor."""
    import pymongo
    logger.info("Initializing database indexes...")
    logger.info(f"Database instance type: {type(db)}")
    try:
        # Check if MockDatabase is being used (MockDatabase doesn't support index creation)
        if hasattr(db, "_collections"): 
            logger.info("Skipping index creation on MockDatabase.")
            return

        # 1. Users Indexes
        await db["users"].create_index([("email", pymongo.ASCENDING)], unique=True)

        # 2. Activities Indexes
        await db["activities"].create_index([("user_id", pymongo.ASCENDING), ("date", pymongo.DESCENDING)])

        # 3. Carbon Predictions Indexes
        await db["carbon_predictions"].create_index([("user_id", pymongo.ASCENDING), ("target_date", pymongo.ASCENDING)], unique=True)


        # 5. Challenges Indexes
        await db["challenges"].create_index([("user_id", pymongo.ASCENDING), ("quest_title", pymongo.ASCENDING)])

        # 6. Leaderboard Indexes
        await db["leaderboard"].create_index([("user_id", pymongo.ASCENDING)], unique=True)
        await db["leaderboard"].create_index([("monthly_co2_kg", pymongo.ASCENDING)])

        # 7. Bill Analyses Indexes
        await db["bill_analyses"].create_index([("user_id", pymongo.ASCENDING), ("billing_period", pymongo.ASCENDING)])

        # 8. Room Analyses Indexes
        await db["room_analyses"].create_index([("user_id", pymongo.ASCENDING), ("analyzed_at", pymongo.DESCENDING)])

        # 9. Chat History Indexes
        await db["chat_history"].create_index([("user_id", pymongo.ASCENDING), ("updated_at", pymongo.DESCENDING)])

        # 10. Carbon Twin Simulations Indexes
        await db["carbon_twin_simulations"].create_index([("user_id", pymongo.ASCENDING), ("simulated_at", pymongo.DESCENDING)])
        
        # 11. API Cache Indexes
        await db["api_cache"].create_index([("key", pymongo.ASCENDING)], unique=True)
        
        logger.info("Database indexes created successfully.")
    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")


