from fastapi import FastAPI, Query
from pydantic import BaseModel, HttpUrl
from typing import List
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import snscrape.modules.twitter as sntwitter

app = FastAPI(title="India Rescue Updates Scraper API")

class RescueUpdate(BaseModel):
    title: str
    summary: str
    source: str
    date: str
    url: HttpUrl

class RescueUpdatesResponse(BaseModel):
    updates: List[RescueUpdate]

# --------- Web Scrapers ---------
async def scrape_pib(query: str) -> List[RescueUpdate]:
    url = "https://pib.gov.in/PressReleasePage.aspx"
    results = []
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
    return results

async def scrape_sikkim(query: str) -> List[RescueUpdate]:
    url = "https://sikkim.gov.in/media/press-release"
    results = []
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
    return results

# --------- Twitter Scraper ---------
def scrape_twitter(query: str, max_results: int = 10) -> List[RescueUpdate]:
    handles = ["PIB_India", "ndmaindia", "adgpi"]
    results = []
    search_query = f"{query} (" + " OR ".join([f'from:{h}' for h in handles]) + ")"
    for tweet in sntwitter.TwitterSearchScraper(search_query).get_items():
        if len(results) >= max_results:
            break
        results.append(RescueUpdate(
            title=tweet.content[:80] + "...",
            summary=tweet.content,
            source=tweet.user.username,
            date=str(tweet.date.date()),
            url=tweet.url
        ))
    return results

# --------- API Endpoint ---------
@app.get("/rescue-updates", response_model=RescueUpdatesResponse, operation_id="fetchRescueUpdates")
async def get_rescue_updates(query: str = Query(..., description="Search query like 'Sikkim' or 'rescue'")):
    pib_updates = await scrape_pib(query)
    sikkim_updates = await scrape_sikkim(query)
    twitter_updates = scrape_twitter(query)
    all_updates = pib_updates + sikkim_updates + twitter_updates
    sorted_updates = sorted(all_updates, key=lambda x: x.date, reverse=True)
    return RescueUpdatesResponse(updates=sorted_updates[:8])
