from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from typing import List
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import subprocess
import json

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
# Scrapers for Web News
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
        print(f"[❌ PIB ERROR] {e}")
    return results

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
        print(f"[❌ SIKKIM ERROR] {e}")
    return results

async def scrape_ndtv(query: str) -> List[RescueUpdate]:
    results = []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://www.ndtv.com/latest")
            soup = BeautifulSoup(r.text, 'html.parser')
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

async def scrape_india_today(query: str) -> List[RescueUpdate]:
    results = []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://www.indiatoday.in/india")
            soup = BeautifulSoup(r.text, 'html.parser')
            for div in soup.select("div.catagory-listing")[:20]:
                a = div.find("a")
                if a:
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

async def scrape_times_now(query: str) -> List[RescueUpdate]:
    results = []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://www.timesnownews.com/india")
            soup = BeautifulSoup(r.text, 'html.parser')
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
# Twitter Scraper — CLI + 72 Hour Filter
# -------------------------
def scrape_twitter_critical_terms(max_results: int = 15) -> List[RescueUpdate]:
    query_terms = [
        '"Lt Col Sandhu"', '"Aarti Sandhu"', '"Amayra Sandhu"',
        '#SikkimRescue', '#MissingFamily',
        '"woman rescued Sikkim"', '"bodies found Sikkim"',
        '"family missing in Sikkim"', '"Indian Army Sikkim rescue"'
    ]
    query = " OR ".join(query_terms)
    since = (datetime.utcnow() - timedelta(hours=72)).strftime('%Y-%m-%d')
    results = []

    try:
        cmd = [
            "snscrape", "--jsonl", "--max-results", str(max_results),
            "--since", since, "twitter-search", query
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in process.stdout:
            tweet = json.loads(line)
            results.append(RescueUpdate(
                title=tweet["content"][:80] + "...",
                summary=tweet["content"],
                source=tweet["user"]["username"],
                date=tweet["date"][:10],
                url=tweet["url"]
            ))
            if len(results) >= max_results:
                break
    except Exception as e:
        print(f"[❌ TWITTER SCRAPE ERROR] {e}")

    return results

# -------------------------
# Unified Endpoint
# -------------------------
@app.get("/rescue-updates", response_model=RescueUpdatesResponse, operation_id="fetchRescueUpdates")
async def get_rescue_updates(query: str = Query(..., description="Search for 'Sikkim', 'rescue', 'Sandhu', etc.")):
    try:
        pib = await scrape_pib(query)
        sikkim = await scrape_sikkim(query)
        ndtv = await scrape_ndtv(query)
        india_today = await scrape_india_today(query)
        times_now = await scrape_times_now(query)
        twitter = scrape_twitter_critical_terms()
        all_updates = pib + sikkim + ndtv + india_today + times_now + twitter
        sorted_updates = sorted(all_updates, key=lambda x: x.date, reverse=True)
        return RescueUpdatesResponse(updates=sorted_updates[:10])
    except Exception as e:
        print(f"[❌ API ERROR] {e}")
        raise
        @app.get("/rss-summary", response_model=RescueUpdatesResponse, operation_id="getRssSummary")
async def get_rss_summary():
    keywords = [
        "aarti sandhu", "lt col sandhu", "amayra", 
        "bodies found", "rescued", "indian army", "sikkim"
    ]
    results = []

    async def fetch(url: str, source_name: str, selector: str):
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url)
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.select(selector)[:25]:
                    title = a.get_text(strip=True)
                    link = a.get("href", "")
                    if any(k.lower() in title.lower() for k in keywords):
                        if not link.startswith("http"):
                            link = url + link
                        results.append(RescueUpdate(
                            title=title,
                            summary=title,
                            source=source_name,
                            date=datetime.now().strftime("%Y-%m-%d"),
                            url=link
                        ))
        except Exception as e:
            print(f"[❌ {source_name} RSS ERROR] {e}")

    await fetch("https://www.ndtv.com/latest", "NDTV", ".news_Itm a")
    await fetch("https://www.indiatoday.in/india", "India Today", ".catagory-listing a")
    await fetch("https://timesofindia.indiatimes.com/india", "Times of India", "a")
    await fetch("https://www.timesnownews.com/india", "Times Now", "a")
    await fetch("https://pib.gov.in/PressReleasePage.aspx", "PIB India", ".content-area ul li a")

    sorted_results = sorted(results, key=lambda x: x.date, reverse=True)
    return RescueUpdatesResponse(updates=sorted_results[:10])

