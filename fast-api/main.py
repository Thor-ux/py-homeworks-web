from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

app = FastAPI(title="Buy/Sell Ads Service")

ads = {}
ad_id_counter = 1

class Advertisement(BaseModel):
    title: str
    description: str
    price: float
    author: str

class AdvertisementResponse(Advertisement):
    id: int
    date_of_creation: str

@app.post("/advertisement", response_model=AdvertisementResponse)
def create_ad(ad: Advertisement):
    global ad_id_counter
    new_ad = ad.dict()
    new_ad['id'] = ad_id_counter
    new_ad['date_of_creation'] = datetime.utcnow().isoformat()
    
    ads[ad_id_counter] = new_ad
    ad_id_counter += 1
    return new_ad

@app.get("/advertisement/{advertisement_id}", response_model=AdvertisementResponse)
def get_ad(advertisement_id: int):
    ad = ads.get(advertisement_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    return ad

@app.patch("/advertisement/{advertisement_id}", response_model=AdvertisementResponse)
def update_ad(advertisement_id: int, ad_update: Advertisement):
    ad = ads.get(advertisement_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    
    updated_fields = ad_update.dict(exclude_unset=True)
    ad.update(updated_fields)
    return ad

@app.delete("/advertisement/{advertisement_id}")
def delete_ad(advertisement_id: int):
    if advertisement_id not in ads:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    del ads[advertisement_id]
    return {"message": "Advertisement deleted successfully"}

@app.get("/advertisement", response_model=List[AdvertisementResponse])
def search_ads(
    title: Optional[str] = None,
    description: Optional[str] = None,
    author: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    results = list(ads.values())
    
    if title:
        results = [ad for ad in results if title.lower() in ad['title'].lower()]
    if description:
        results = [ad for ad in results if description.lower() in ad['description'].lower()]
    if author:
        results = [ad for ad in results if author.lower() in ad['author'].lower()]
    if min_price is not None:
        results = [ad for ad in results if ad['price'] >= min_price]
    if max_price is not None:
        results = [ad for ad in results if ad['price'] <= max_price]
    
    return results
