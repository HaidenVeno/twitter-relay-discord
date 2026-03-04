# Twitter/X → Discord Bot

Polls an RSSHub feed for [@beardedhost](https://x.com/beardedhost) and posts new tweets as embeds in a Discord channel.


## Setup

RSSHub (Docker)

RSSHub converts the Twitter/X profile into an RSS feed. You need a valid X session cookie to authenticate.

**To get ye' auth token:**

1.  Log into [x.com](https://x.com/) in your browser
2.  Open DevTools → Application → Cookies → `twitter.com`
3.  Snag the value of the `auth_token` cookie
4.  Save it under the rsshub.env file `TWITTER_AUTH_TOKEN=your_token_here`

**Run RSSHub:**

```bash
docker run -d -p 1200:1200 --env-file rsshub.env --restart unless-stopped diygod/rsshub
```
I suggest using something like docker secrets for the rsshub/twitter auth token. 

Verify it works via `http://localhost:1200/twitter/user/beardedhost` in the browser

### 2. The Bot

**Create the bot:**

1.  Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2.  New Application → Bot → Reset Token → copy the token
3.  Enable **Message Content Intent** under Privileged Gateway Intents
4.  Invite the bot via OAuth2 → URL Generator with scopes: `bot` and permissions: `Send Messages`, `Embed Links`, `View Channels` this is all it needs

### 3. Configure

Create the `.env` with the correct values (the FEED_URL will change if using this for another user/business)

```env
DISCORD_BOT_TOKEN=bot_token_here
DISCORD_CHANNEL_ID=channel_id_here
FEED_URL=http://localhost:1200/twitter/user/beardedhost
POLL_INTERVAL_MINUTES=15
```

### 4. Install & Run

```bash
pip install -r requirements.txt
python bot.py

```

## Notes

-   On first run the bot seeds existing feed entries without posting them to avoid flooding, there is a commented out section that can be uncommented for initial testing.
-   The RSSHub auth token expires when your X session expires `auth_token` cookie and restart the RSSHub container with the new value, approximately 6 months if Twitter isn't being nasty. 
-   `seen_ids` is in-memory only but the bot won't double-post on restart but it will re-seed on startup

## Deploying

Just ensure RSSHub is running on the same host and `FEED_URL` points to `http://localhost:1200/...`.
