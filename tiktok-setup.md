# TikTok Publishing — Setup Guide

Get the TikTok publisher working. End goal: fill these in `config.yml` →

- `tiktok.client_key`
- `tiktok.client_secret`

…then run `python3 scripts/tiktok_login.py` once to authorize (it writes `tiktok_token.json`).

We use **inbox/draft mode**: the app uploads your comic reel to your TikTok **drafts**, and you tap _Post_ in the TikTok app. This path works **without TikTok app review** — the painful audit that Direct Post needs.

> Temporary scratch guide — delete once you're set up.

---

## 0. Prerequisites

- [x] A TikTok account (any normal account works for inbox mode)
- [x] `pip install -r requirements.txt` (adds `requests`)
- [x] ffmpeg installed (`brew install ffmpeg`) — builds the reel video

---

## 1. Create a TikTok developer app

1. Go to https://developers.tiktok.com/ and **log in** with your TikTok account.
2. Open the developer portal: https://developers.tiktok.com/apps/
3. Click **Connect an app** / **Create an app**. Give it a name (e.g. `comic-generator`).
4. Fill the basic app info it asks for (description, category). You do **not** need to submit for review for inbox mode.

✅ Checkpoint: an app exists in your TikTok developer portal.

---

## 2. Add the Content Posting API product + scopes

1. In your app → **Add products** → add **Content Posting API**.
2. In the app's **Scopes**, enable:
   - `video.upload` ← required for inbox/draft mode
   - (`video.publish` is only needed for Direct Post, which requires audit — skip it for now)
3. Also make sure **Login Kit** is available (it's how we authorize). Enable scope `user.info.basic` if offered.

✅ Checkpoint: Content Posting API added, `video.upload` scope enabled.

---

## 3. Register the redirect URI

TikTok's **Login Kit → Redirect URI → Web** tab only accepts **`https://`** URLs, so a
`http://127.0.0.1:8080/callback` localhost callback **cannot be registered there** — TikTok
rejects the whole login with a generic `client_key` error if the `redirect_uri` you send
doesn't exactly match a registered one. So we register an https URL we control and let the
login helper use its paste-the-redirected-URL flow.

1. In your app settings → **Login Kit** → **Redirect URI** → **Web**, add an https URL you
   own. A raw file in this repo works fine (it just needs to exist and return 200):
   ```
   https://raw.githubusercontent.com/<you>/ComicGenerator/main/terms/index.md
   ```
2. Save.
3. Put that **exact** URL in `config.yml` under `tiktok.redirect_uri` so the login script
   sends the matching value:
   ```yaml
   tiktok:
     redirect_uri: "https://raw.githubusercontent.com/<you>/ComicGenerator/main/terms/index.md"
   ```

> The helper auto-detects that this isn't a localhost URL and switches to "paste the
> redirected URL" mode: after you approve in the browser, TikTok lands on that https page
> with `?code=...` in the address bar — copy the whole URL back into the terminal.

✅ Checkpoint: an https Redirect URI is registered **and** the identical string is in
`tiktok.redirect_uri`.

---

## 4. Copy your client key & secret into config.yml

1. In the app dashboard, find **Client key** and **Client secret** (under app credentials / "Manage apps").
2. Paste them into `config.yml`:
   ```yaml
   tiktok:
     enabled: true
     mode: inbox
     client_key: "PASTE_CLIENT_KEY"
     client_secret: "PASTE_CLIENT_SECRET"
   ```

✅ Checkpoint: `client_key` and `client_secret` set.

---

## 5. (Sandbox) add yourself as a target user

While the app is unaudited it runs in **Sandbox**. Add your own TikTok account as a test user so uploads are allowed:

1. App dashboard → **Sandbox** (or **Target users / Test users**).
2. Add/authorize your TikTok handle.

✅ Checkpoint: your account is a test user of the app.

---

## 6. Authorize (one-time) — run the login helper

From the project root:

```bash
python3 scripts/tiktok_login.py
```

What happens:

1. Your browser opens the TikTok authorization page → approve.
2. TikTok redirects to your registered https URL with `?code=...` in the address bar.
3. Copy that **full** URL and paste it back into the terminal when prompted.
4. The helper exchanges the code and writes **`tiktok_token.json`** (access + refresh token).

The redirect URI comes from `tiktok.redirect_uri` in config (step 3). To override it for one
run, pass `--redirect-uri <url>` — it must still exactly match a registered one.

✅ Checkpoint: `tiktok_token.json` exists and the script printed `scope: ...,video.upload`.

---

## 7. Generate + publish

```bash
python -m src.main --idea "A vampire detective investigates a murder at a midnight concert" --publish
```

Or generate, then answer the prompt (since `enabled: true`):

```bash
python -m src.main --idea "..."
# → Publish to TikTok? [y/N]
```

Expected console flow:

```
[4/4] Publishing to TikTok...
      Building reel video...
      Initializing TikTok draft upload...
      Uploading video to TikTok...
      Uploaded to your TikTok drafts (publish_id=...).
      → Open the TikTok app → Inbox/Notifications → finish & post.
```

Then on your phone: open TikTok → **Inbox/Notifications** (or Profile → drafts) → the comic reel is waiting → add any final caption → **Post**.

---

## Going public automatically (later, optional)

To skip the manual tap and post straight to the profile, switch to Direct Post:

- Set `tiktok.mode: direct`, enable scope `video.publish`, re-run `scripts/tiktok_login.py`.
- **Requires TikTok app audit.** Until audited, direct posts are forced to `privacy_level: SELF_ONLY` (only you see them). `tiktok.privacy_level` controls this.

---

## Troubleshooting

| Symptom                                     | Fix                                                                                        |
| ------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `client_key / client_secret are not set`    | Fill them in config.yml (step 4)                                                           |
| `No TikTok access token found`              | Run `python3 scripts/tiktok_login.py` (step 6)                                             |
| Redirect URI mismatch error in browser      | The URI in step 3 must **exactly** match the one the script uses (`--redirect-uri`)        |
| `Es ist etwas schiefgelaufen` / generic `client_key` error **after** login | `redirect_uri` sent ≠ a registered one. Make `tiktok.redirect_uri` exactly equal a Login Kit **Web** (https) Redirect URI (step 3). |
| `Es ist etwas schiefgelaufen` / generic `client_key` error **after** login | `redirect_uri` sent ≠ a registered one. Make `tiktok.redirect_uri` exactly equal a Login Kit **Web** (https) Redirect URI (step 3). |
| `scope_not_authorized` / upload rejected    | `video.upload` not enabled, or you're not a Sandbox test user (steps 2, 5)                 |
| Token refresh fails                         | Refresh token expired → re-run the login helper                                            |
| `unaudited_client_can_only_post_to_private` | Direct mode only — expected until audit; keep `privacy_level: SELF_ONLY` or use inbox mode |

## Notes / limits

- **Inbox mode = one manual tap** to publish (by design, no audit).
- Tokens: access token ~24h, refresh token ~365d; the app refreshes automatically using `tiktok_token.json`.
- Video must be a real MP4 (the pipeline's `build_reel` output is fine); single-page comics still become a short reel.
