import os, secrets, sqlite3, hashlib, hmac, time, json, urllib.parse
from pathlib import Path
from datetime import datetime, timezone, timedelta

import httpx
import stripe
from fastapi import FastAPI, HTTPException, Request, Response, Cookie
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

BASE = Path(__file__).parent
DB_PATH = Path(os.getenv("DATABASE_PATH", str(BASE / "finora.db")))
if str(DB_PATH).find("/") >= 0:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

APP_SECRET = os.getenv("APP_SECRET", "dev-only-change-me")
TWELVE_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
COINGECKO_KEY = os.getenv("COINGECKO_API_KEY", "")
ALPHA_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
if STRIPE_SECRET:
    stripe.api_key = STRIPE_SECRET

app = FastAPI(title="Finora API", version="0.3.0")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          salt TEXT NOT NULL,
          premium INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions(
          token TEXT PRIMARY KEY,
          user_id INTEGER NOT NULL,
          expires_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS holdings(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          name TEXT NOT NULL,
          ticker TEXT NOT NULL,
          asset_type TEXT NOT NULL,
          units REAL NOT NULL,
          avg_price REAL NOT NULL,
          currency TEXT NOT NULL DEFAULT 'EUR',
          last_price REAL,
          last_price_at TEXT,
          source TEXT
        );
        CREATE TABLE IF NOT EXISTS watchlist(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          ticker TEXT NOT NULL,
          name TEXT NOT NULL,
          asset_type TEXT NOT NULL,
          UNIQUE(user_id,ticker)
        );
        CREATE TABLE IF NOT EXISTS journal(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          ticker TEXT NOT NULL,
          date TEXT NOT NULL,
          horizon TEXT NOT NULL,
          thesis TEXT NOT NULL
        );
        """)
init_db()

def pbkdf(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 220_000).hex()

def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(48)
    with db() as c:
        c.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",
                  (token, user_id, int(time.time()) + 60*60*24*30))
    return token

def current_user(request: Request):
    token = request.cookies.get("finora_session")
    if not token:
        raise HTTPException(401, "Inicia sesión.")
    with db() as c:
        row = c.execute("""SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
                           WHERE s.token=? AND s.expires_at>?""", (token, int(time.time()))).fetchone()
    if not row:
        raise HTTPException(401, "Sesión expirada.")
    return row

class AuthIn(BaseModel):
    email: str
    password: str = Field(min_length=8)

class HoldingIn(BaseModel):
    name: str
    ticker: str
    asset_type: str = "Otro"
    units: float = Field(gt=0)
    avg_price: float = Field(ge=0)
    currency: str = "EUR"

class WatchIn(BaseModel):
    ticker: str
    name: str
    asset_type: str = "Otro"

class JournalIn(BaseModel):
    ticker: str
    date: str
    horizon: str
    thesis: str = Field(min_length=10)

@app.get("/")
def home():
    return FileResponse(BASE/"static"/"index.html")

@app.post("/api/register")
def register(data: AuthIn, response: Response):
    email = data.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "Email no válido.")
    salt = secrets.token_bytes(16)
    ph = pbkdf(data.password, salt)
    try:
        with db() as c:
            cur = c.execute("INSERT INTO users(email,password_hash,salt,created_at) VALUES(?,?,?,?)",
                            (email, ph, salt.hex(), datetime.now(timezone.utc).isoformat()))
            uid = cur.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Ese email ya está registrado.")
    token = create_session(uid)
    response.set_cookie("finora_session", token, httponly=True, samesite="lax",
                        secure=APP_BASE_URL.startswith("https://"), max_age=60*60*24*30)
    return {"ok": True, "premium": False, "email": email}

@app.post("/api/login")
def login(data: AuthIn, response: Response):
    email = data.email.strip().lower()
    with db() as c:
        u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not u or not hmac.compare_digest(pbkdf(data.password, bytes.fromhex(u["salt"])), u["password_hash"]):
        raise HTTPException(401, "Email o contraseña incorrectos.")
    token = create_session(u["id"])
    response.set_cookie("finora_session", token, httponly=True, samesite="lax",
                        secure=APP_BASE_URL.startswith("https://"), max_age=60*60*24*30)
    return {"ok": True, "premium": bool(u["premium"]), "email": email}

@app.post("/api/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("finora_session")
    if token:
        with db() as c: c.execute("DELETE FROM sessions WHERE token=?", (token,))
    response.delete_cookie("finora_session")
    return {"ok": True}

@app.get("/api/me")
def me(request: Request):
    u = current_user(request)
    return {"id": u["id"], "email": u["email"], "premium": bool(u["premium"])}

async def twelve_quote(symbol: str):
    if not TWELVE_KEY:
        return None
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get("https://api.twelvedata.com/quote",
                             params={"symbol": symbol, "apikey": TWELVE_KEY})
    if r.status_code != 200: return None
    d = r.json()
    try:
        return {"price": float(d["close"]), "currency": d.get("currency"), "time": d.get("datetime"),
                "source": "Twelve Data"}
    except Exception:
        return None

async def twelve_search(q: str):
    if not TWELVE_KEY: return []
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get("https://api.twelvedata.com/symbol_search",
                             params={"symbol": q, "apikey": TWELVE_KEY})
    if r.status_code != 200: return []
    d = r.json()
    return [{"symbol":x.get("symbol"),"name":x.get("instrument_name") or x.get("name"),
             "type":x.get("instrument_type"),"exchange":x.get("exchange"),
             "currency":x.get("currency")} for x in (d.get("data") or [])[:30]]

async def coingecko_price(symbol: str):
    sid={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","BNB":"binancecoin","XRP":"ripple","ADA":"cardano","DOGE":"dogecoin"}.get(symbol.upper())
    if not sid: return None
    headers={"x-cg-demo-api-key":COINGECKO_KEY} if COINGECKO_KEY else {}
    async with httpx.AsyncClient(timeout=10) as client:
        r=await client.get("https://api.coingecko.com/api/v3/simple/price",
                           params={"ids":sid,"vs_currencies":"eur","include_last_updated_at":"true"},
                           headers=headers)
    if r.status_code!=200:return None
    d=r.json().get(sid)
    if not d:return None
    return {"price":float(d["eur"]),"currency":"EUR",
            "time":datetime.fromtimestamp(d.get("last_updated_at",time.time()),tz=timezone.utc).isoformat(),
            "source":"CoinGecko"}

async def quote(symbol: str, asset_type: str):
    if asset_type.lower()=="cripto":
        q=await coingecko_price(symbol)
        if q:return q
    return await twelve_quote(symbol)

@app.get("/api/quotes")
async def quotes(request: Request, symbols: str = ""):
    current_user(request)
    syms=[x.strip().upper() for x in symbols.split(",") if x.strip()][:30]
    out={}
    for s in syms:
        q=await twelve_quote(s)
        if q: out[s]=q
    return out

@app.get("/api/search")
async def search(request: Request, q: str = ""):
    current_user(request)
    q=q.strip()[:60]
    if not q:return []
    return await twelve_search(q)

@app.get("/api/holdings")
async def get_holdings(request: Request):
    u=current_user(request)
    with db() as c:
        rows=c.execute("SELECT * FROM holdings WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/holdings")
async def add_holding(data: HoldingIn, request: Request):
    u=current_user(request)
    with db() as c:
        cur=c.execute("""INSERT INTO holdings(user_id,name,ticker,asset_type,units,avg_price,currency)
                         VALUES(?,?,?,?,?,?,?)""",
                      (u["id"],data.name,data.ticker.upper(),data.asset_type,data.units,data.avg_price,data.currency))
    return {"ok":True,"id":cur.lastrowid}

@app.delete("/api/holdings/{hid}")
def delete_holding(hid:int,request:Request):
    u=current_user(request)
    with db() as c: c.execute("DELETE FROM holdings WHERE id=? AND user_id=?",(hid,u["id"]))
    return {"ok":True}

@app.post("/api/holdings/refresh")
async def refresh_holdings(request: Request):
    u=current_user(request)
    with db() as c: rows=c.execute("SELECT * FROM holdings WHERE user_id=?",(u["id"],)).fetchall()
    updated=[]
    for r in rows:
        q=await quote(r["ticker"],r["asset_type"])
        if q:
            with db() as c:
                c.execute("""UPDATE holdings SET last_price=?, last_price_at=?, source=? WHERE id=? AND user_id=?""",
                          (q["price"],q["time"],q["source"],r["id"],u["id"]))
            updated.append({"ticker":r["ticker"],**q})
    return {"updated":updated}

@app.get("/api/watchlist")
def get_watch(request:Request):
    u=current_user(request)
    with db() as c: rows=c.execute("SELECT * FROM watchlist WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/watchlist")
def add_watch(data:WatchIn,request:Request):
    u=current_user(request)
    with db() as c:
        try:c.execute("INSERT INTO watchlist(user_id,ticker,name,asset_type) VALUES(?,?,?,?)",(u["id"],data.ticker.upper(),data.name,data.asset_type))
        except sqlite3.IntegrityError: pass
    return {"ok":True}

@app.delete("/api/watchlist/{wid}")
def del_watch(wid:int,request:Request):
    u=current_user(request)
    with db() as c:c.execute("DELETE FROM watchlist WHERE id=? AND user_id=?",(wid,u["id"]))
    return {"ok":True}

@app.get("/api/news")
async def news(request:Request, ticker:str=""):
    current_user(request)
    if not ALPHA_KEY:
        return {"configured":False,"articles":[],"message":"Configura ALPHAVANTAGE_API_KEY para noticias en directo."}
    params={"function":"NEWS_SENTIMENT","limit":"25","apikey":ALPHA_KEY}
    if ticker:
        params["tickers"]=ticker.upper()
    async with httpx.AsyncClient(timeout=15) as client:
        r=await client.get("https://www.alphavantage.co/query",params=params)
    if r.status_code!=200:return {"configured":True,"articles":[],"message":"Error consultando proveedor de noticias."}
    d=r.json()
    arts=[]
    for a in d.get("feed",[])[:25]:
        arts.append({"title":a.get("title"),"source":a.get("source"),
                     "url":a.get("url"),"published":a.get("time_published"),
                     "summary":a.get("summary","")[:400]})
    return {"configured":True,"articles":arts}

@app.get("/api/journal")
def journal_get(request:Request):
    u=current_user(request)
    with db() as c:r=c.execute("SELECT * FROM journal WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall()
    return [dict(x) for x in r]

@app.post("/api/journal")
def journal_add(data:JournalIn,request:Request):
    u=current_user(request)
    with db() as c:c.execute("""INSERT INTO journal(user_id,ticker,date,horizon,thesis) VALUES(?,?,?,?,?)""",
                              (u["id"],data.ticker.upper(),data.date,data.horizon,data.thesis))
    return {"ok":True}

@app.get("/api/premium")
def premium(request:Request):
    u=current_user(request)
    return {"premium":bool(u["premium"])}

@app.post("/api/premium/checkout")
def premium_checkout(request:Request):
    u=current_user(request)
    if not STRIPE_SECRET or not STRIPE_PRICE_ID:
        return JSONResponse({"demo":True,"message":"Stripe no está configurado. Añade las variables STRIPE_* para pagos reales."})
    session=stripe.checkout.Session.create(
        mode="subscription", line_items=[{"price":STRIPE_PRICE_ID,"quantity":1}],
        success_url=APP_BASE_URL+"/?premium=success",
        cancel_url=APP_BASE_URL+"/?premium=cancelled",
        customer_email=u["email"],
        metadata={"user_id":str(u["id"])}
    )
    return {"url":session.url}

@app.post("/api/stripe/webhook")
async def stripe_webhook(request:Request):
    payload=await request.body()
    sig=request.headers.get("stripe-signature")
    if not STRIPE_SECRET or not STRIPE_WEBHOOK_SECRET:
        return {"received":True,"configured":False}
    try:event=stripe.Webhook.construct_event(payload,sig,STRIPE_WEBHOOK_SECRET)
    except Exception as e:raise HTTPException(400,str(e))
    obj=event["data"]["object"]
    if event["type"] in ("checkout.session.completed","customer.subscription.created","customer.subscription.updated"):
        uid=(obj.get("metadata") or {}).get("user_id")
        if uid:
            with db() as c:c.execute("UPDATE users SET premium=1 WHERE id=?",(int(uid),))
    if event["type"] in ("customer.subscription.deleted",):
        # Production: map Stripe customer/subscription to the Finora user before downgrading.
        uid=(obj.get("metadata") or {}).get("user_id")
        if uid:
            with db() as c:c.execute("UPDATE users SET premium=0 WHERE id=?",(int(uid),))
    return {"received":True}

@app.get("/api/health")
def health():
    return {"ok":True,"market_provider":bool(TWELVE_KEY),"crypto_provider":bool(COINGECKO_KEY),
            "news_provider":bool(ALPHA_KEY),"stripe":bool(STRIPE_SECRET and STRIPE_PRICE_ID)}
