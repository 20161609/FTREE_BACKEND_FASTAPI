# External Libraries
from app.db.model import Authentification
from app.firebase.storage import delete_storage_uid
from firebase_admin import firestore, auth
from email.mime.text import MIMEText
from app.db.init import database
import smtplib
from typing import Optional
from app.firebase.auth import verify_code, signup_firebase, send_verify_code, withdraw_firebase
from app.firebase.auth import get_uid_from_token
from app.db.crud import create_auth_postgre, delete_all_branch_postgre, delete_all_transaction_postgre, delete_user_postgre, upload_branch
from app.db.crud import get_auth_postgre
import requests
import asyncio
from fastapi import APIRouter, HTTPException, Body, Header, Query
from dotenv import load_dotenv
import os

load_dotenv()
FIREBASE_API_KEY=os.getenv("FIREBASE_API_KEY")
FIREBASE_SIGNUP_URL=os.getenv("FIREBASE_SIGNUP_URL")
MAIN_EMAIL=os.getenv("MAIN_EMAIL")
MAIN_EMAIL_PASSWORD=os.getenv("MAIN_EMAIL_PASSWORD")

router = APIRouter()

# Sign in
@router.post("/signin/")
async def signin(data: dict=Body(...)):
    url = f"{FIREBASE_SIGNUP_URL}{FIREBASE_API_KEY}"
    response = requests.post(url, json={
        "email": data['email'],
        "password": data['password'],
        "returnSecureToken": True
    })

    response_data = response.json()
    await asyncio.sleep(2)

    if response.status_code == 200:
        id_token = response_data['idToken']
        res_uid = await get_uid_from_token(id_token)
        uid = res_uid['uid']
        if uid == None:
            raise HTTPException(status_code=400, detail=res_uid['message'])

        user_info = await get_auth_postgre(uid)
        print('user_info:', user_info)
        # email, name = user_info.email, user_info.username
        email, name = 'email', 'user_info'
        return {"status":True, "message":{
            "id_token": id_token, 'email':email, 'name':name
        }}
    else:
        raise HTTPException(
            status_code=response.status_code, 
            detail=response_data['error']['message']
        )

# Sign up
@router.post("/signup/")
async def signup(data: dict=Body(...)):
    # Firebase service to create user and store information in database
    email = data['email']
    password = data['password']
    username = data['username']
    code = data['code']

    # Check if code is valid
    try:
        verification = await verify_code({"email": email, "code": code})
        if verification['status'] == False:
            raise HTTPException(status_code=400, detail=verification['message'])
    except Exception as e:
        error_meessage = "When verifying code: " + str(e)
        raise HTTPException(status_code=400, detail=error_meessage)


    # Regester User into firebase
    try:
        uid = await signup_firebase(email, password)
        if uid == None:
            # You don't neet to cancel Signup
            raise HTTPException(status_code=400, detail="Failed to register user into firebase")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))        
    

    # Save user info into postgreSQL
    try:
        res = await create_auth_postgre(uid, email, username)
        if res['status'] == False:
            raise HTTPException(status_code=400, detail=res["message"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str)

    # Update Home Branch in postgreSQL
    try:
        res = await upload_branch(uid=uid, path="Home")
        if res['status'] == False:
            raise HTTPException(status_code=400, detail=res["message"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Sign out from Firebase
@router.post("/signout/")
async def signout(authorization: Optional[str] = Header(None)):
    try:
        # Extract Uid from ID Token
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        uid = res_uid['uid']
        if uid == None:
            raise HTTPException(status_code=400, detail="Invalid token or UID not found")

        # Delete All Receipt images from Firebase Storage
        await auth.revoke_refresh_tokens(uid)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Sign up2 for Next.js
@router.post("/signup2/")
async def signup2(data: dict=Body(...)):
    # Firebase service to create user and store information in database
    email = data['email']
    password = data['password']
    username = data['username']

    # Regester User into firebase
    try:
        uid = await signup_firebase(email, password)
        if uid == None:
            # You don't neet to cancel Signup
            raise HTTPException(status_code=400, detail="Failed to register user into firebase")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))        
    

    # Save user info into postgreSQL
    try:
        res = await create_auth_postgre(uid, email, username)
        if res['status'] == False:
            raise HTTPException(status_code=400, detail=res["message"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str)

    # Update Home Branch in postgreSQL
    try:
        res = await upload_branch(uid=uid, path="Home")
        if res['status'] == False:
            raise HTTPException(status_code=400, detail=res["message"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# Check Verification Code
@router.post("/check-verify-code/")
async def check_verify_code(data: dict=Body(...)):
    try:
        email = data['email']
        code = data['code']
        verification = await verify_code({"email": email, "code": code})
        if verification['status'] == False:
            raise HTTPException(status_code=400, detail=verification['message'])
        return {"message": "Code verified successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Send Verification Code
@router.post("/verify-email/")
async def sendVerifyCode(data: dict=Body(...)):
    # Use signup_firebase
    try:
        # If user already exists, return error
        email = data['email']
        await send_verify_code(email)
        return {"message": "Code sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# If the user already exists, return error
@router.get("/check-user-exist/")
async def user_exist(data: dict=Body(...)):
    try:
        email = data['email']
        user = auth.get_user_by_email(email)
        if user:
            raise HTTPException(status_code=400, detail="User already exists")
        return
    except Exception as e:
        return {"message": "User does not exist"}

# Check User Exist version 2 for Next.js
@router.get("/check-user-exist2/")
async def user_exist2(email: str=Query(...)):
    try:
        user = auth.get_user_by_email(email)
        if user:
            return False
        return True
    except Exception as e:
        return True
    
# Modify Password - Execution
@router.post("/modify-password/")
async def modify_password(authorization: Optional[str] = Header(None), data: dict=Body(...)):
    try:
        # Extract Id Token from Header
        id_token = authorization.split(" ")[1]

        # Extract Values from Body
        email = data['email']
        code = data['code']
        new_password = data['new_password']

        # Get uid from ID token
        res_uid = await get_uid_from_token(id_token)
        user = auth.get_user_by_email(email)
        uid = res_uid['uid']
        if uid == None:
            raise HTTPException(status_code=400, detail=res_uid['message'])
        elif uid != user.uid:
            raise HTTPException(status_code=400, detail="Invalid ID token")

        # Check if code is valid
        verification = await verify_code({"email": email, "code": code})
        if verification['status'] == False:
            raise HTTPException(status_code=400, detail=verification['message'])
        print(verification['message'])

        # Update Password
        uid = user.uid
        auth.update_user(uid, password=new_password)
        return {"message": "Password modified successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# Modify Password - Verify Email
@router.get("/modify-password-email")
async def modify_password_email(email: str = Query(...)):
    try:
        # Find the user in Firebase by email
        user = auth.get_user_by_email(email)
        
        if not user:
            raise HTTPException(status_code=400, detail="User not found")

        # Retrieve additional user data from PostgreSQL
        user_info = await get_auth_postgre(user.uid)
        username = user_info.username
        
        # Generate password reset link
        link = auth.generate_password_reset_link(email)

        # Create email content
        msg = MIMEText(f"""
        Dear {username},

        We received a request to reset your password for your Finance-Tree account. You can reset your password by clicking the link below:

        {link}

        If you did not request a password reset, please ignore this email. Your password will remain unchanged.

        Thank you,
        Finance-Tree
        """)
        msg['Subject'] = 'Password Reset Request'
        msg['From'] = MAIN_EMAIL
        msg['To'] = email

        # Send the email using SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(MAIN_EMAIL, MAIN_EMAIL_PASSWORD)
            server.sendmail(MAIN_EMAIL, email, msg.as_string())
        
        return {"message": "Password reset email sent successfully."}

    except auth.AuthError as e:
        if e.code == 'RESET_PASSWORD_EXCEED_LIMIT':
            # Handle the specific case where password reset requests exceed the limit
            raise HTTPException(status_code=429, detail="Too many password reset requests. Please try again later.")
        else:
            # Handle other Firebase Auth related errors
            raise HTTPException(status_code=400, detail="An error occurred with Firebase Auth: " + str(e))
    
    except Exception as e:
        # Catch any other exceptions
        raise HTTPException(status_code=400, detail="An error occurred: " + str(e))

# Withdraw
@router.delete("/withdraw/")
async def withdraw(authorization: Optional[str] = Header(None)):
    try:
        # Extract Uid from ID Token
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        uid = res_uid['uid']
        if uid == None:
            raise HTTPException(status_code=400, detail=res_uid['message'])

        # Delete All Receipt images from Firebase Storage
        await delete_storage_uid(uid)

        # Delete User info from PostgreSQL
        await delete_all_branch_postgre(uid)
        await delete_all_transaction_postgre(uid)
        await delete_user_postgre(uid)

        # Delete User from Firebase
        await withdraw_firebase(uid)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/user-info/")
async def get_user_info(authorization: Optional[str] = Header(None)):
    try:
        # Extract Uid from ID Token
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        uid = res_uid['uid']
        if uid == None:
            raise HTTPException(status_code=400, detail=res_uid['message'])

        # Get User Info from PostgreSQL
        user_info = await get_auth_postgre(uid)
        return {
            'email': user_info.email, 
            'username': user_info.username, 
            'useai': user_info.useai
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/update-userinfo/')
async def update_userinfo(authorization: Optional[str] = Header(None), data: dict=Body(...)):
    try:
        # Extract Uid from ID Token
        id_token = authorization.split(" ")[1]
        res_uid = await get_uid_from_token(id_token)
        uid = res_uid['uid']
        if uid == None:
            raise HTTPException(status_code=400, detail=res_uid['message'])

        # Update User Info in PostgreSQL
        query = Authentification.__table__.update().where(Authentification.uid == uid).values(
            username=data['username'],
            useai=data['useai']
        )
        await database.execute(query)
        return {"message": "User info updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
