from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.firebase.init import initialize_firebase
from app.db.init import database
from app.api import user, db

app = FastAPI()

# Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to the database on startup
@app.on_event("startup")
async def startup():
    print("Connecting to the database")
    await database.connect()

# Disconnect from the database on shutdown
@app.on_event("shutdown")
async def shutdown():
    print("Disconnecting from the database")
    await database.disconnect()

# # Initialize Firebase
initialize_firebase()

# # Register routes
app.include_router(user.router, prefix="/user")
app.include_router(db.router, prefix="/db")

@app.get("/")
async def root():
    return {"message": "Welcome to my FastAPI project!"}
