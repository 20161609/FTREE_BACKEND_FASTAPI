from fastapi import HTTPException
import datetime
from email.mime.text import MIMEText
import smtplib
import secrets
from firebase_admin import auth
from firebase_admin import credentials, auth, db, storage, firestore
from dotenv import load_dotenv
import os

load_dotenv()
FIREBASE_API_KEY=os.getenv("FIREBASE_API_KEY")
FIREBASE_SIGNUP_URL=os.getenv("FIREBASE_SIGNUP_URL")
MAIN_EMAIL=os.getenv("MAIN_EMAIL")
MAIN_EMAIL_PASSWORD=os.getenv("MAIN_EMAIL_PASSWORD")

# register user into firebase
async def signup_firebase(email, password):
    try:
        return auth.create_user(
            email=email,
            password=password,
        ).uid
    except Exception as e:
        return None

# Update user email verified status
def update_user_email_verified_status(email: str):
    uid_ref = db.reference('Authentification').order_by_child('email').equal_to(email).get()
    if uid_ref:
        for uid, data in uid_ref.items():
            db.reference(f'Authentification/{uid}').update({
                'email_verified': True
            })
            return {"message": "User email verified"}

    raise ValueError("User not found")

# Get user info by uid
def get_user_by_uid(uid: str):
    try:
        return auth.get_user(uid)
    except:
        return None

# Code verification
async def verify_code(user: dict):
    email = user['email']
    code = user['code']
    doc_ref = firestore.client().collection('verificationCodes').document(email)
    doc = doc_ref.get()

    stored_data = doc.to_dict()
    stored_code = stored_data.get('code')
    timestamp = stored_data.get('timestamp')

    # Convert: Firestore Timestamp -> datetime.datetime
    if isinstance(timestamp, datetime.datetime):
        timestamp = timestamp.replace(tzinfo=None)

    # Check expiration about code (15 minutes)
    now = datetime.datetime.utcnow()
    code_age = (now - timestamp).total_seconds()

    if code_age > 900: # 900s = 15m
        return {"status": False, "message": "Code expired"}

    if stored_code != code:
        return {"status": False, "message": "Invalid code"}

    # Successful Verification: Firestore
    doc_ref.delete()  # delete code already used

    return {"status":True, "message": "Verification successful"}

# Send email including verification code
async def send_verify_code(email: str):
    # Generate random verification code
    code = secrets.token_hex(3)

    # Store temproary code in Firestore
    try:
        firestore.client().collection('verificationCodes').document(email).set({
            'code': code,
            'timestamp': firestore.SERVER_TIMESTAMP,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Send email
    try:
        msg = MIMEText(f'Your verification code is: {code}')
        msg['Subject'] = 'Verification Code'
        msg['From'] = MAIN_EMAIL
        msg['To'] = email

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(MAIN_EMAIL, MAIN_EMAIL_PASSWORD)
            server.sendmail(MAIN_EMAIL, email, msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Verification of ID Token
async def get_uid_from_token(idToken: str) -> str:
    try:
        # Use Firebase Admin SDK
        decoded_token = auth.verify_id_token(idToken)
        uid = decoded_token['uid']
        return {'uid':uid, 'message': 'ID token is valid'}
    except auth.InvalidIdTokenError:
        return {'uid': None, 'message': 'Invalid ID token'}
    except auth.ExpiredIdTokenError:
        return {'uid': None, 'message': 'Expired ID token'}
    except auth.RevokedIdTokenError:
        return {'uid': None, 'message': 'Revoked ID token'}
    except Exception as e:
        return {'uid': None, 'message': f"Failed to verify ID token: {str(e)}"}

# Withdraw user from Firebase
async def withdraw_firebase(uid: str):
    try:
        auth.delete_user(uid)
        return {"status": True, "message": "User deleted successfully"}
    except Exception as e:
        return {"status": False, "message": "Failed to delete user from Firebase\n"+str(e)}