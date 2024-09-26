import base64
from app.firebase.auth import get_uid_from_token
from app.db.crud import delete_branch_postgre, delete_branch_transaction_postgre, delete_transaction_postgre, get_children_postgre, get_daily_postgre, get_monthly_postgre, get_tree_postgre
from app.db.crud import is_exist_branch
from app.db.crud import add_branch
from app.db.crud import add_transaction_postgre

from app.firebase.storage import get_hashed_uid
from firebase_admin import firestore, auth
from firebase_admin import storage
from fastapi import Query, UploadFile, File

import secrets
import requests
import asyncio
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, HTTPException, Body, Header, Form
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter()

# Get Tree
@router.get("/get-tree/")
async def get_tree(authorization: Optional[str] = Header(None)):
    # Extract id_token from the header
    if authorization is None or not authorization.startswith("Bearer "):
        return {"status": False, "message": "No ID token provided"}
    id_token = authorization.split(" ")[1]

    # Get uid from id_token
    try:
        res_uid = await get_uid_from_token(id_token)
        if res_uid['uid'] is None:
            return {"status": False, "message": res_uid['message']}
        uid = res_uid['uid']
    except Exception as e:
        raise Exception(f"Failed to get uid from id_token: {e}")

    # Refer PostgreSQL and get tree data
    try:
        tree = await get_tree_postgre(uid)
        return tree
    except Exception as e:
        raise Exception(f"Failed to get tree from postgreSQL: {e}")
        
# Create Branch
@router.post("/create-branch/")
async def create_branch(authorization: Optional[str] = Header(None), data: dict=Body(...)):
    # Extract id_token from the header
    if authorization is None or not authorization.startswith("Bearer "):
        return {"status": False, "message": "No ID token provided"}
    id_token = authorization.split(" ")[1]

    # Get uid from id_token
    try:
        res_uid = await get_uid_from_token(id_token)
        if res_uid['uid'] is None:
            return {"status": False, "message": res_uid['message']}
        uid = res_uid['uid']
    except Exception as e:
        raise Exception(f"Failed to get uid from id_token: {e}")

    # Check if path is valid
    is_exist = await is_exist_branch(uid, data['branch'])
    if not is_exist:
        raise HTTPException(status_code=400, detail=f"not valid path - {data['branch']}")
    
    # Already Exist?
    already_exist = await is_exist_branch(uid, data['branch'] + '/' + data['child_name'])
    if already_exist:
        raise HTTPException(status_code=400, detail="Child already exists")

    # Execute Mkdir
    await add_branch(uid, data['branch'] + '/' + data['child_name'])

# Get Daily Transaction
@router.get("/refer-daily/")
async def refer_daily(authorization: Optional[str] = Header(None), data: dict = Body(...)):
    # Get uid from id token
    try:
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        uid = res_uid['uid']
    except:
        raise Exception("Failed to get uid from id_token")
    
    # Get transaction from Postgre
    try:
        branch = data['branch']
        begin_date = data['begin_date']
        end_date = data['end_date']

        result = await get_daily_postgre(
            uid=uid, branch=branch, begin_date=begin_date, end_date=end_date)

        if result == None:
            raise Exception("Failed to get transaction from Postgre")
        else:
            return result
    except Exception as e:
        raise Exception(f"Failed to get daily transaction from postgreSQL: {e}")

# Get Daily Transaction2 - Parameters should be Query
@router.get("/refer-daily2/")
async def refer_daily2(authorization: Optional[str] = Header(None), branch: str = Query(...), begin_date: str = Query(...), end_date: str = Query(...)):
    # Get uid from id token
    try:
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        uid = res_uid['uid']
    except:
        raise Exception("Failed to get uid from id_token")

    # Get transaction from Postgre
    try:
        result = await get_daily_postgre(
            uid=uid, branch=branch, begin_date=begin_date, end_date=end_date)
        if result == None:
            raise Exception("Failed to get transaction from Postgre")
        else:
            return result
    except Exception as e:
        raise Exception(f"Failed to get daily transaction from postgreSQL: {e}")

# Get Monthly Transaction
@router.get("/refer-monthly")
async def refer_monthly(authorization: Optional[str] = Header(None), data: dict = Body(...)):
    # Get uid from id token
    try:
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        uid = res_uid['uid']
    except:
        raise Exception("Failed to get uid from id_token")
    
    # Get transaction from Postgre
    try:
        branch = data['branch']
        begin_date = data['begin_date']
        end_date = data['end_date']
        result = await get_monthly_postgre(
            uid=uid, branch=branch, begin_date=begin_date, end_date=end_date)
        if result == None:
            raise Exception("Failed to get transaction from Postgre")
        
        return result
    except Exception as e:
        raise Exception(f"Failed to get monthly transaction from postgreSQL: {e}")

# Upload Transaction and Receipt
@router.post("/upload-transaction/")
async def upload_transaction(
    authorization: Optional[str] = Header(None),
    t_date: str = Form(...),
    branch: str = Form(...),
    cashflow: int = Form(...),
    description: str = Form(...),
    receipt: UploadFile = File(None)):

    # Extract id_token from the header
    try:
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        if res_uid['uid'] is None:
            raise HTTPException(status_code=400, detail=res_uid['message'])
        uid = res_uid['uid']
    except Exception as e:
        raise Exception(f"Failed to get uid from id_token: {e}")
    
    # Add transaction to Postgre
    try:
        timestamp = int(datetime.now().timestamp())
        code = secrets.token_hex(3)
        hashed_uid = get_hashed_uid(uid)
        FILE_NAME = f"{hashed_uid}_{timestamp}_{code}.jpeg"

        tid = await add_transaction_postgre({
            't_date': date.fromisoformat(t_date),
            'branch': branch, 'cashflow': cashflow,
            'description': description, 'receipt': FILE_NAME,
            'c_date': datetime.now(), 'uid': uid
        })
    except Exception as e:
        raise Exception(f"Failed to add transaction to postgreSQL: {e}")
    
    # Upload receipt to Firebase
    try:
        bucket = storage.bucket()
        blob = bucket.blob(FILE_NAME)
        blob.upload_from_string(receipt.file.read(), content_type='image/jpeg')
    except Exception as e:
        # Remove transaction from Postgre
        await delete_transaction_postgre(uid, tid)
        raise Exception(f"Failed to upload receipt to Firebase: {e}")
    
    return {"message": "Transaction successfully uploaded."}

# Delete Transaction with tid
@router.delete("/delete-transaction/")
async def delete_transaction(authorization: Optional[str] = Header(None), data: dict = Body(...)):
    # Extract id_token from the header
    try:
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        if res_uid['uid'] is None:
            raise HTTPException(status_code=400, detail=res_uid['message'])
        uid = res_uid['uid']
    except Exception as e:
        raise Exception(f"Failed to get uid from id_token: {e}")
    
    # Delete transaction from Postgre
    try:
        await delete_transaction_postgre(uid, data['tid'])
    except Exception as e:
        raise Exception(f"Failed to delete transaction from postgreSQL: {e}")

# Load Receipt
@router.get("/get-receipt")
async def load_receipt(authorization: Optional[str] = Header(None), data: dict = Body(...)):
    # Get uid from id token
    try:
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        uid = res_uid['uid']
        if uid is None:
            raise Exception(res_uid['message'])
    except Exception as e:
        raise Exception(f"Failed to get uid from id_token: {e}")
    
    # Load image from Firebase Storage
    try:
        bucket = storage.bucket()
        blob = bucket.blob(data['file_path'])
        image = blob.download_as_bytes()
        return base64.b64encode(image).decode('utf-8')   
    except Exception as e:
        raise Exception(f"Failed to load image from Firebase Storage: {e}")
    
# Load Receipt2 for Next.js
@router.get("/get-receipt2")
async def load_receipt(authorization: Optional[str] = Header(None), file_path: str = Query(...)):
    # Get uid from id token
    try:
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        uid = res_uid['uid']
        if uid is None:
            raise Exception(res_uid['message'])
    except Exception as e:
        raise Exception(f"Failed to get uid from id_token: {e}")
    
    # Load image from Firebase Storage
    try:
        bucket = storage.bucket()
        blob = bucket.blob(file_path)
        image_url = blob.generate_signed_url(version="v4", expiration=3600)
        return image_url
    except Exception as e:
        raise Exception(f"Failed to load image from Firebase Storage: {e}")

# Modify Transaction
@router.put('/modify-transaction')
async def modify_transaction(authorization: Optional[str] = Header(None), tid: int = Form(...), 
    t_date: str = Form(...), branch: str = Form(...), cashflow: int = Form(...),
    description: Optional[str] = Form(None), receipt: Optional[UploadFile] = File(None)):

    # Extract id_token from the header
    try:
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        if res_uid['uid'] is None:
            raise HTTPException(status_code=400, detail=res_uid['message'])
        uid = res_uid['uid']
    except Exception as e:
        raise Exception(f"Failed to get uid from id_token: {e}")

    # Delete Original Transaction
    try:
        delt_data = await delete_transaction_postgre(uid, tid)
    except Exception as e:
        raise Exception(f"Failed to delete original transaction: {e}")

    # Delete Image File
    if delt_data['receipt'] is None:
        try:
            delt_file_path = delt_data['receipt']
            bucket = storage.bucket()
            blob = bucket.blob(delt_file_path)
            blob.delete()
        except Exception as e:
            # Restore Transaction
            await add_transaction_postgre({
                't_date': delt_data['t_date'], 'branch': delt_data['branch'], 
                'cashflow': delt_data['cashflow'], 'description': delt_data['description'], 
                'receipt': delt_data['receipt'], 'c_date': delt_data['c_date'], 'uid': delt_data['uid']
            })
            raise Exception(f"Failed to delete image file: {e}")

    # Add Modified Transaction
    try:
        await upload_transaction(
            authorization=authorization, t_date=t_date, branch=branch,
            cashflow=cashflow, description=description, receipt=receipt
        )
    except Exception as e:
        raise Exception(f"Failed to add modified transaction: {e}")
        
@router.delete("/delete-branch")
async def delete_branch(authorization: Optional[str] = Header(None), data: dict = Body(...)):
    # Extract id_token from the header
    try:
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        if res_uid['uid'] is None:
            raise HTTPException(status_code=400, detail=res_uid['message'])
        uid = res_uid['uid']
    except Exception as e:
        raise Exception(f"Failed to get uid from id_token: {e}")
    
    # Get Children from Postgre
    try:
        children = await get_children_postgre(uid, data['branch'])
    except Exception as e:
        raise Exception(f"Failed to get Children List from postgreSQL: {e}")
    
    # Delete Branch
    try:
        for child in children:
            await delete_branch_postgre(uid, child['bid'])
    except Exception as e:
        raise Exception(f"Failed to delete branch from postgreSQL: {e}")
    
    # Delete Transaction
    del_list = []
    try:
        for child in children:
            box = await delete_branch_transaction_postgre(uid=uid, branch=child['path'])
            for b in box:
                del_list.append(b)
    except Exception as e:
        # Restore Branch
        for child in children:
            await add_branch(uid, child['path'])
        raise Exception(f"Failed to delete transaction from postgreSQL: {e}")
    
    # Delete Image File
    try:
        for item in del_list:
            bucket = storage.bucket()
            blob = bucket.blob(item['receipt'])
            blob.delete()
    except:
        # Restore Branch
        for child in children:
            await add_branch(uid, child['path'])

        # Restore Transaction
        for item in del_list:
            await add_transaction_postgre({
                't_date': item['t_date'], 'branch': item['branch'], 
                'cashflow': item['cashflow'], 'description': item['description'], 
                'receipt': item['receipt'], 'c_date': item['c_date'], 'uid': item['uid']
            })

        raise Exception("Failed to delete image file")
    
    print("Branch Deleted - ", data['branch'])