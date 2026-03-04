"""
bot.py — Twitter/X RSS → Discord Embed Bot
Polls an RSS feed for @beardedhost and posts new tweets as embeds.

Dependencies:
    pip install -r requirements.txt
"""

import os
import discord
from discord.ext import tasks
import feedparser
import aiohttp
import asyncio
import re
import hashlib
from html import unescape
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()


BOT_TOKEN     = os.getenv("DISCORD_BOT_TOKEN")
FEED_URL      = os.getenv("FEED_URL", "http://localhost:1200/twitter/user/beardedhost")
CHANNEL_ID    = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_MINUTES", "15"))
EMBED_COLOR   = 0xF5A623  # golden-ish yellow


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Check your .env file!")
if not CHANNEL_ID:
    raise RuntimeError("CHANNEL_ID is not set. Check your .env file!")


intents = discord.Intents.default()
client  = discord.Client(intents=intents)
seen_ids: set[str] = set()


def entry_id(entry) -> str:
    key = getattr(entry, "id", None) or getattr(entry, "link", "") or entry.get("title", "")
    return hashlib.md5(key.encode()).hexdigest()


def parse_published(entry) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def extract_image(summary_raw: str) -> str | None:
# video tweets
    match = re.search(r'<video[^>]+poster="([^"]+)"', summary_raw)
    if not match:
# image tweets        
        match = re.search(r'<img[^>]+src="([^"]+)"', summary_raw)
    if match:
        return unescape(match.group(1))
    return None


def build_embed(entry) -> discord.Embed:
    title       = getattr(entry, "title", "New Tweet")
    link        = getattr(entry, "link", "")
    summary_raw = getattr(entry, "summary", "")
# strips html tags
    summary = re.sub(r"<[^>]+>", "", summary_raw).strip()
# removes blank lines
    #summary = re.sub(r"\n{3,}", "\n\n", summary) 
    image_url = extract_image(summary_raw)

# fallback to media content
    if not image_url and hasattr(entry, "media_content") and entry.media_content:
        image_url = unescape(entry.media_content[0].get("url", ""))

    embed = discord.Embed(
        description=summary or title,
        color=EMBED_COLOR,
        timestamp=parse_published(entry),
        url=link,
    )
    embed.set_author(
        name="@beardedhost",
        url="https://x.com/beardedhost",
        icon_url="https://pbs.twimg.com/profile_images/1937555073967468544/oPDbAP7N_400x400.jpg",
    )
    embed.set_footer(
        text="Twitter / X",
        icon_url="https://abs.twimg.com/favicons/twitter.3.ico",
    )

    if image_url:
        embed.set_image(url=image_url)
    if link:
        embed.add_field(name="", value=f"[View on X]({link})", inline=False)

    return embed


@tasks.loop(minutes=POLL_INTERVAL)
async def poll_feed():
    global seen_ids
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"[TwitterFeed] Channel {CHANNEL_ID} not found.")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(FEED_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    print(f"[TwitterFeed] Feed returned HTTP {resp.status}")
                    return
                raw = await resp.text()
    except Exception as e:
        print(f"[TwitterFeed] Failed to fetch feed: {e}")
        return

    feed = feedparser.parse(raw)
    if not feed.entries:
        print("[TwitterFeed] No entries in feed.")
        return

   # first run — this will flood all posts use for debugging
    #if not seen_ids:
        #seen_ids.add("initialized")
        #print("[TwitterFeed] First run, posting existing entries.")

    if not seen_ids:
        seen_ids = {entry_id(e) for e in feed.entries}
        print(f"[TwitterFeed] Seeded {len(seen_ids)} existing entries, watching for new ones.")
        return

    new_entries = [e for e in reversed(feed.entries) if entry_id(e) not in seen_ids]
    for entry in new_entries:
        try:
            await channel.send(embed=build_embed(entry))
            seen_ids.add(entry_id(entry))
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[TwitterFeed] Failed to post: {e}")


@poll_feed.before_loop
async def before_poll():
    await client.wait_until_ready()


@client.event
async def on_ready():
    print(f"[TwitterFeed] Logged in as {client.user} — polling every {POLL_INTERVAL}m")
    poll_feed.start()


client.run(BOT_TOKEN)