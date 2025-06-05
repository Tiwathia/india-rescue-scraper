from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from typing import List
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import snscrape.modules.twitter as sntwitter
import os

app = FastAPI(title="India Rescue Updates Scraper API")

# Serve static files like action.json and openapi.yaml for GPT
app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------------
# Data Models
# -------------------------
class RescueUpdate(BaseModel):
    title: str
    summary: str
    source: str
    date: str
    url: HttpUrl

class RescueUpdatesResponse(BaseModel):
    updates: List[RescueUpdate]

# -------------------------
# Scraper: PIB
# -------------------------
async def scrape_pib(query: str) -> List[RescueUpdate]:
    url = "https://pib.gov.in/PressReleasePage.aspx"
    results = []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            items = soup.select(".content-area ul li a")
            for item in items[:20]:
                title = item.get_text(strip=True)
                link = "https://pib.gov.in/" + item['href'].lstrip('/')
                if query.lower() in title.lower():
                    results.append(RescueUpdate(
                        title=title,
                        summary=title,
                        source="PIB India",
                        date=datetime.now().strftime("%Y-%m-%d"),
                        url=link
                    ))
    except Exception as e:
        print(f"[❌ PIB ERROR] {e}")
    return results

# -------------------------
# Scraper: Sikkim Government
# -------------------------
async def scrape_sikkim(query: str) -> List[RescueUpdate]:
    url = "https://sikkim.gov.in/media/press-release"
    results = []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            items = soup.select(".news-content a")
            for item in items[:20]:
                title = item.get_text(strip=True)
                link = item['href']
                if not link.startswith("http"):
                    link = "https://sikkim.gov.in" + link
                if query.lower() in title.lower():
                    results.append(RescueUpdate(
                        title=title,
                        summary=title,
                        source="Sikkim Govt",
                        date=datetime.now().strftime("%Y-%m-%d"),
                        url=link
                    ))
    except Exception as e:
        print(f"[❌ SIKKIM ERROR] {e}")
    return results

# -------------------------
# Scraper: Twitter
# -------------------------
def scrape_twitter_critical_terms(max_results: int = 15) -> List[RescueUpdate]:
    terms = [
        '"Lt Col Sandhu"',
        '"Aarti Sandhu"',
        '"Amayra Sandhu"',
        '"woman with child rescued Sikkim"',
        '"Sikkim rescue family found"',
        '"body found Sikkim"',
        '"retired Indian Air Force Sikkim"',
        '"missing family Sikkim"',
        '"child rescued Sikkim"'
    ]
    combined_query = " OR ".join(terms)
    results = []
    try:
        for tweet in sntwitter.TwitterSearchScraper(combined_query).get_items():
            if len(results) >= max_results:
                break
            results.append(RescueUpdate(
                title=tweet.content[:80] + "...",
                summary=tweet.content,
                source=tweet.user.username,
                date=str(tweet.date.date()),
                url=tweet.url
            ))
    except Exception as e:
        print(f"[❌ TWITTER ERROR] {e}")
    return results

# -------------------------
# API Endpoint
# -------------------------
@app.get("/rescue-updates", response_model=RescueUpdatesResponse, operation_id="fetchRescueUpdates")
async def get_rescue_updates(query: str = Query(..., description="Search query like 'Sikkim' or 'rescue'")):
    try:
        pib_updates = await scrape_pib(query)
        sikkim_updates = await scrape_sikkim(query)
        twitter_updates = scrape_twitter_critical_terms()
        all_updates = pib_updates + sikkim_updates + twitter_updates
        sorted_updates = sorted(all_updates, key=lambda x: x.date, reverse=True)
        print(f"[✅ SUCCESS] Total results: {len(sorted_updates)}")
        return RescueUpdatesResponse(updates=sorted_updates[:8])
    except Exception as e:
        print(f"[❌ API ERROR] {e}")
        raise
