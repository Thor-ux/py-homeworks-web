from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt

SECRET_KEY = ""
ALGORITHM = ""
ACCESS_TOKEN_EXPIRE_HOURS = 48

app = FastAPI(title="Buy/Sell Ads Service")

users = {}
ads = {}
user_id_counter = 1
ad_id_counter = 1

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserBase(BaseModel):
    username: str
    group: str  # 'user' or 'admin'

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    group: Optional[str] = None

class Advertisement(BaseModel):
    title: str
    description: str
    price: float

class AdvertisementResponse(Advertisement):
    id: int
    author: int
    date_of_creation: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def create_access_token(user_id: int, group: str):
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "group": group, "exp": expire}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"]), payload["group"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.split()[1]
    user_id, group = decode_access_token(token)
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.post("/user", response_model=UserResponse)
def create_user(user: UserCreate):
    global user_id_counter
    if user.group not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid group")
    hashed_password = pwd_context.hash(user.password)
    new_user = {
        "id": user_id_counter,
        "username": user.username,
        "password_hash": hashed_password,
        "group": user.group
    }
    users[user_id_counter] = new_user
    user_id_counter += 1
    return UserResponse(**new_user)

@app.get("/user/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user)

@app.patch("/user/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate, current_user=Depends(get_current_user)):
    target_user = users.get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if current_user["group"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if user_update.username:
        target_user["username"] = user_update.username
    if user_update.password:
        target_user["password_hash"] = pwd_context.hash(user_update.password)
    if user_update.group:
        if current_user["group"] != "admin":
            raise HTTPException(status_code=403, detail="Only admin can change group")
        if user_update.group not in ["user", "admin"]:
            raise HTTPException(status_code=400, detail="Invalid group")
        target_user["group"] = user_update.group

    return UserResponse(**target_user)

@app.delete("/user/{user_id}")
def delete_user(user_id: int, current_user=Depends(get_current_user)):
    target_user = users.get(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user["group"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    del users[user_id]
    return {"message": "User deleted successfully"}

@app.post("/login", response_model=TokenResponse)
def login(form_data: UserCreate):
    user = next((u for u in users.values() if u["username"] == form_data.username), None)
    if not user or not pwd_context.verify(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(user["id"], user["group"])
    return TokenResponse(access_token=token)

@app.post("/advertisement", response_model=AdvertisementResponse)
def create_ad(ad: Advertisement, current_user=Depends(get_current_user)):
    global ad_id_counter
    new_ad = ad.dict()
    new_ad["id"] = ad_id_counter
    new_ad["author"] = current_user["id"]
    new_ad["date_of_creation"] = datetime.utcnow().isoformat()
    ads[ad_id_counter] = new_ad
    ad_id_counter += 1
    return new_ad

@app.get("/advertisement/{ad_id}", response_model=AdvertisementResponse)
def get_ad(ad_id: int):
    ad = ads.get(ad_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    return ad

@app.patch("/advertisement/{ad_id}", response_model=AdvertisementResponse)
def update_ad(ad_id: int, ad_update: Advertisement, current_user=Depends(get_current_user)):
    ad = ads.get(ad_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    
    if current_user["group"] != "admin" and ad["author"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    updated_fields = ad_update.dict(exclude_unset=True)
    ad.update(updated_fields)
    return ad

@app.delete("/advertisement/{ad_id}")
def delete_ad(ad_id: int, current_user=Depends(get_current_user)):
    ad = ads.get(ad_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    
    if current_user["group"] != "admin" and ad["author"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    del ads[ad_id]
    return {"message": "Advertisement deleted successfully"}

@app.get("/advertisement", response_model=List[AdvertisementResponse])
def search_ads(
    title: Optional[str] = None,
    description: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    author_id: Optional[int] = None
):
    results = list(ads.values())
    if title:
        results = [ad for ad in results if title.lower() in ad["title"].lower()]
    if description:
        results = [ad for ad in results if description.lower() in ad["description"].lower()]
    if min_price is not None:
        results = [ad for ad in results if ad["price"] >= min_price]
    if max_price is not None:
        results = [ad for ad in results if ad["price"] <= max_price]
    if author_id is not None:
        results = [ad for ad in results if ad["author"] == author_id]
    return results
