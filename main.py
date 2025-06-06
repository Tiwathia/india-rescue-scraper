from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from typing import List
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import snscrape.modules.twitter as sntwitter

app = FastAPI(title="India Rescue Updates Scraper API")

# Mount static folder for GPT Actions
app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------------
# Response Models
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
# Web Scraper: PIB
# -------------------------
async def scrape_pib(query: str) -> List[RescueUpdate]:
    results = []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://pib.gov.in/PressReleasePage.aspx")
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
        print(f"[PIB ERROR] {e}")
    return results

# -------------------------
# Web Scraper: Sikkim Gov
# -------------------------
async def scrape_sikkim(query: str) -> List[RescueUpdate]:
    results = []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://sikkim.gov.in/media/press-release")
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
        print(f"[SIKKIM ERROR] {e}")
    return results

# -------------------------
# Web Scraper: NDTV
# -------------------------
async def scrape_ndtv(query: str) -> List[RescueUpdate]:
    results = []
    try:
