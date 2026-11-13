import sys, os
sys.path.insert(0, os.path.abspath("backend"))
from app.core.database import SessionLocal
from app.models.document import Document
from app.services.storage import storage_service

db = SessionLocal()
doc = db.query(Document).filter(Document.id == '8c0f2998-002b-4b77-80f7-318d51790e6c').first()
if doc:
    if storage_service.is_supabase:
        storage_service.supabase_client.delete_file(doc.stored_filename)
    db.delete(doc)
    db.commit()
    print("Test doc deleted successfully.")
else:
    print("Doc not found.")
db.close()
