from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from passlib.hash import bcrypt
import os
import psycopg2
import random
import json

app = FastAPI()

DATABASE_URL = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ---------- DB SETUP ----------
cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT,
    inventory TEXT,
    gradient INT,
    entropy INT
)
""")
conn.commit()

# Create owner TTL
cur.execute("SELECT * FROM users WHERE username='TTL'")
if not cur.fetchone():
    cur.execute("INSERT INTO users VALUES (%s,%s,%s,%s,%s,%s)",
                ("TTL", bcrypt.hash("0955"), "owner", "[]", 999, 999))
    conn.commit()

class UserData(BaseModel):
    username: str
    password: str

# ---------- ENDPOINTS ----------
@app.post("/register")
def register(data: UserData):
    cur.execute("SELECT * FROM users WHERE username=%s",(data.username,))
    if cur.fetchone(): raise HTTPException(400,"User exists")
    cur.execute("INSERT INTO users VALUES (%s,%s,%s,%s,%s,%s)",
                (data.username, bcrypt.hash(data.password), "player","[]",0,0))
    conn.commit()
    return {"ok":True}

@app.post("/login")
def login(data: UserData):
    cur.execute("SELECT password,role FROM users WHERE username=%s",(data.username,))
    row = cur.fetchone()
    if not row or not bcrypt.verify(data.password,row[0]): raise HTTPException(401,"Invalid")
    return {"username":data.username,"role":row[1]}

@app.post("/generate")
def generate(username: str):
    cur.execute("SELECT inventory FROM users WHERE username=%s",(username,))
    row = cur.fetchone()
    if not row: raise HTTPException(404,"No user")
    inv=json.loads(row[0])
    rarity=random.choices(["normal","neon","limited"],[70,20,10])[0]
    card={"hex":"#"+format(random.randint(0,0xFFFFFF),'06x'),"rarity":rarity}
    inv.append(card)
    cur.execute("UPDATE users SET inventory=%s WHERE username=%s",(json.dumps(inv),username))
    conn.commit()
    return card

@app.get("/inventory")
def inventory(username:str):
    cur.execute("SELECT inventory FROM users WHERE username=%s",(username,))
    row=cur.fetchone()
    if not row: raise HTTPException(404,"No user")
    return json.loads(row[0])

@app.post("/sacrifice")
def sacrifice(username:str):
    cur.execute("SELECT inventory,gradient,entropy FROM users WHERE username=%s",(username,))
    row=cur.fetchone()
    if not row: raise HTTPException(404,"No user")
    inv=json.loads(row[0])
    if len(inv)==0: raise HTTPException(400,"No cards")
    inv.pop()
    gradient=row[1]+1
    entropy=row[2]+1
    cur.execute("UPDATE users SET inventory=%s,gradient=%s,entropy=%s WHERE username=%s",
                (json.dumps(inv),gradient,entropy,username))
    conn.commit()
    return {"gradient":gradient,"entropy":entropy}
