import streamlit as st
import snscrape.modules.twitter as sntwitter
import pandas as pd
from datetime import datetime, timedelta

st.title("Sikkim Landslide Twitter Updates")

keywords = [
    "Sikkim landslide", "Teesta flood", "Chungthang", "Sikkim rescue", 
    "#SikkimLandslide", "#Teesta", "#SikkimFlood", "Sikkim missing"
]

search_query = " OR ".join(keywords) + f" since:{(datetime.utcnow()-timedelta(days=3)).strftime('%Y-%m-%d')}"

max_tweets = 100

tweets = []
for tweet in sntwitter.TwitterSearchScraper(search_query).get_items():
    tweets.append({
        "Date": tweet.date.strftime("%Y-%m-%d %H:%M"),
        "User": tweet.user.username,
        "Text": tweet.content,
        "Link": tweet.url
    })
    if len(tweets) >= max_tweets:
        break

df = pd.DataFrame(tweets)

if len(df) > 0:
    st.write(f"Showing {len(df)} most recent tweets with relevant keywords:")
    st.dataframe(df[["Date", "User", "Text"]])
    for i, row in df.iterrows():
        st.markdown(f"- **[{row['User']}]({row['Link']})**: {row['Text']}")
else:
    st.write("No recent tweets found. Try again later or with different keywords.")
