from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from typing import List
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import snscrape.modules.twitter as sntwitter

app = FastAPI(title="India Rescue Updates Scraper API")
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
# Scraper: NDTV
# -------------------------
async def scrape_ndtv(query: str) -> List[RescueUpdate]:
    url = "https://www.ndtv.com/latest"
    results = []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select(".news_Itm a")[:20]:
                title = a.get_text(strip=True)
                link = a['href']
                if query.lower() in title.lower():
                    results.append(RescueUpdate(
                        title=title,
                        summary=title,
                        source="NDTV",
                        date=datetime.now().strftime("%Y-%m-%d"),
                        url=link
                    ))
    except Exception as e:
        print(f"[❌ NDTV ERROR] {e}")
    return results

# -------------------------
# Scraper: India Today
# -------------------------
async def scrape_india_today(query: str) -> List[RescueUpdate]:
    url = "https://www.indiatoday.in/india"
    results = []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            soup = BeautifulSoup(r.text, "html.parser")
            for div in soup.select("div.catagory-listing")[:20]:
                a = div.find("a")
                if not a: continue
                title = a.get_text(strip=True)
                link = "https://www.indiatoday.in" + a["href"]
                if query.lower() in title.lower():
                    results.append(RescueUpdate(
                        title=title,
                        summary=title,
                        source="India Today",
                        date=datetime.now().strftime("%Y-%m-%d"),
                        url=link
                    ))
    except Exception as e:
        print(f"[❌ INDIA TODAY ERROR] {e}")
    return results

# -------------------------
# Scraper: Times Now
# -------------------------
async def scrape_times_now(query: str) -> List[RescueUpdate]:
    url = "https://www.timesnownews.com/india"
    results = []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select("a")[:20]:
                title = a.get_text(strip=True)
                link = a.get("href", "")
                if title and query.lower() in title.lower() and "timesnownews" in link:
                    results.append(RescueUpdate(
                        title=title,
                        summary=title,
                        source="Times Now",
                        date=datetime.now().strftime("%Y-%m-%d"),
                        url=link
                    ))
    except Exception as e:
        print(f"[❌ TIMES NOW ERROR] {e}")
    return results

# -------------------------
# Scraper: Twitter (Expanded)
# -------------------------
def scrape_twitter_critical_terms(max_results: int = 15) -> List[RescueUpdate]:
    terms = [
        '"Lt Col Sandhu"',
        '"Aarti Sandhu"',
        '"Amayra Sandhu"',
        '#SikkimRescue',
        '#MissingFamily',
        '#SikkimFlood',
        '"bodies found Sikkim"',
        '"rescued woman Sikkim"',
        '"family missing in Sikkim"',
        '"Indian Army rescue Sikkim"'
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
