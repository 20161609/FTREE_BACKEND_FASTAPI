from datetime import datetime
from operator import or_
from sqlalchemy import Column, String, Integer, Date, String, Text, LargeBinary, ForeignKey, TIMESTAMP
from sqlalchemy.sql import select
from sqlalchemy import func, case, and_
from sqlalchemy import or_, between
from app.db.model import Authentification, Branch, Transaction
from app.db.init import database, Base

# Create Authentification
async def create_auth_postgre(uid:str, email:str, username:str):
    try:
        query = Authentification.__table__.insert().values(
            uid=uid,
            username=username,
            email=email,
            useai=True
        )
        await database.execute(query)
        return {"status": True, "message": "User registered successfully"}
    except Exception as e:
        return {"status": False, "message": "Failed to register user into postgreSQL\n"+str(e)}

# Create Branch
async def upload_branch(uid:str, path:str):
    try:
        query = Branch.__table__.insert().values(
            uid=uid,
            path=path
        )
        await database.execute(query)
        return {"status": True, "message": "Branch uploaded successfully"}
    except Exception as e:
        return {"status": False, "message": "Failed to upload branch\n"+str(e)}

# Create Transaction
async def get_auth_postgre(uid: str):
    query = Authentification.__table__.select().where(Authentification.uid == uid)
    return await database.fetch_one(query)

# Get Tree with uid
async def get_tree_postgre(uid: str):
    query = Branch.__table__.select().where(Branch.uid == uid)
    return await database.fetch_all(query)

# If branch exist
async def is_exist_branch(uid: str, branch: str):
    query = Branch.__table__.select().where(Branch.uid == uid).where(Branch.path == branch)
    return await database.fetch_one(query) is not None

# Add Branch
async def add_branch(uid: str, branch: str):
    query = Branch.__table__.insert().values(uid=uid, path=branch)
    await database.execute(query)

# Add Transaction
async def add_transaction_postgre(transaction: dict):
    query = Transaction.__table__.insert().values(
        t_date=transaction['t_date'],
        branch=transaction['branch'],
        cashflow=transaction['cashflow'],
        description=transaction['description'],
        receipt=transaction['receipt'],
        c_date=transaction['c_date'],
        uid=transaction['uid']
    ).returning(Transaction.__table__.c.tid)
    return await database.execute(query)

# Delete Branch with uid and tid
async def delete_transaction_postgre(uid: str, tid: int):
    try:
        query = Transaction.__table__.delete().where(
                Transaction.uid == uid
            ).where(
                Transaction.tid == tid
            ).returning(Transaction.receipt)
        
        return await database.fetch_one(query)
    except Exception as e:
        print("Failed to delete branch from postgreSQL\n"+str(e))

# Delete Branch with uid and branch
async def delete_branch_transaction_postgre(uid: str, branch: str):
    try:
        query = Transaction.__table__.delete().where(
            (Transaction.uid == uid) & 
            (or_(Transaction.branch == branch, Transaction.branch.like(f'{branch}/%')))
        ).returning(Transaction.__table__.c)
        
        return await database.fetch_all(query)
    except Exception as e:
        raise Exception(f"Failed to delete branch from PostgreSQL: {str(e)}")        

# Delete Branch with uid
async def delete_branch_postgre(uid: str, bid: int):
    try:
        query = Branch.__table__.delete().where(
            Branch.uid == uid
        ).where(
            Branch.bid == bid
        ).returning(Branch.__table__.c)
        return await database.execute(query)
    except Exception as e:
        raise Exception(f"Failed to delete branch from PostgreSQL: {str(e)}")

# Get Children with uid and branch
async def get_children_postgre(uid: str, branch: str):
    # Same or sub-branch
    query = Branch.__table__.select().where(
        (Branch.uid == uid) & 
        (or_(Branch.path.like(f'{branch}/%'), Branch.path == branch))
    )
    return await database.fetch_all(query)

# Get Daily transaction from Postgre
async def get_daily_postgre(uid: str, branch: str, begin_date: str, end_date: str):
    begin_date = datetime.strptime(begin_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # include_branch = branch + '/'
    query = Transaction.__table__.select().where(
        (Transaction.uid == uid) &
        (or_(Transaction.branch == branch, Transaction.branch.like(f'{branch + '/'}%'))) &
        (Transaction.t_date.between(begin_date, end_date))  # Date range filter
    ).order_by(Transaction.t_date)

    results = await database.fetch_all(query)
    
    return [
        {key: item[key] for key in ['tid', 't_date', 'branch', 'cashflow', 'description', 'receipt', 'c_date']}
        for item in results
    ]

# Get Monthly transaction from Postgre
async def get_monthly_postgre(uid: str, branch: str, begin_date: str, end_date: str):
    # Date format conversion
    begin_date = datetime.strptime(begin_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Group by Transaction.t_date
    monthly_label = func.to_char(Transaction.t_date, 'YYYY-MM')
    query = (
        select(
            monthly_label.label('monthly'),  # Month label
            func.sum(
                case(
                    (Transaction.cashflow > 0, Transaction.cashflow),  # Income condition
                    else_=0
                )
            ).label('income'),  # Income sum
            func.sum(
                case(
                    (Transaction.cashflow < 0, Transaction.cashflow),  # 지출 조건
                    else_=0
                )
            ).label('expenditure')  # 지출 합계
        )
        .where( # Filter by uid, branch, and date range
            (Transaction.uid == uid) &
            (Transaction.branch.like(f'{branch}%')) &
            (Transaction.t_date.between(begin_date, end_date))
        )
        .group_by(monthly_label)
        .order_by(monthly_label)
    )
    results = await database.fetch_all(query)

    # Convert the result to a list
    monthly_box = []
    for row in results:
        monthly_box.append({
            'monthly': row['monthly'],
            'income': row['income'],
            'expenditure': abs(row['expenditure'])
        })

    return monthly_box

# Delete All Transaction with uid
async def delete_all_transaction_postgre(uid: str):
    try:
        query = Transaction.__table__.delete().where(
            Transaction.uid == uid
        ).returning(Transaction.receipt)
        return await database.fetch_all(query)
    except Exception as e:
        raise Exception(f"Failed to delete all transactions from PostgreSQL: {str(e)}")

# Delete All Branch with uid
async def delete_all_branch_postgre(uid: str):
    try:
        query = Branch.__table__.delete().where(
            Branch.uid == uid
        ).returning(Branch.path)
        return await database.fetch_all(query)
    except Exception as e:
        raise Exception(f"Failed to delete all branches from PostgreSQL: {str(e)}")

# Delete User with uid
async def delete_user_postgre(uid: str):
    try:
        query = Authentification.__table__.delete().where(
            Authentification.uid == uid
        ).returning(Authentification.uid)
        return await database.fetch_one(query)
    except Exception as e:
        raise Exception(f"Failed to delete user from PostgreSQL: {str(e)}")
    
