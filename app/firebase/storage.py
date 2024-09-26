import hashlib
import secrets
from firebase_admin import storage
from datetime import datetime

def get_hashed_uid(uid: str) -> str:
    # Hash UID with SHA256 to make it unique and not exposed
    hash_object = hashlib.sha256(uid.encode())
    return hash_object.hexdigest()

async def delete_storage_uid(uid: str):
    # Get File Name Format
    hashed_uid = get_hashed_uid(uid)
    basic_file_format = f'{hashed_uid}_'

    # Delete All files from firebase storage, which has name like 'basic_file_format%'
    bucket = storage.bucket()
    blobs = bucket.list_blobs()
    for blob in blobs:
        if basic_file_format in blob.name:
            blob.delete()
            print(f'File {blob.name} deleted')
