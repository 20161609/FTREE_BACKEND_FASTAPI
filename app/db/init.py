import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from databases import Database
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Read the database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

# Set up SQLAlchemy engine and metadata
engine = create_engine(DATABASE_URL)
metadata = MetaData()
Base = declarative_base()

# Create a Database object
database = Database(DATABASE_URL, ssl=False)

# SQLAlchemy session setup
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the database tables
Base.metadata.create_all(bind=engine)
