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

The login helper runs a tiny local web server to catch the OAuth redirect.

1. In your app settings → **Login Kit** / **Redirect URI**, add **exactly**:
   ```
   http://127.0.0.1:8080/callback
   ```
2. Save.

> If TikTok rejects a raw IP/`http`, try `http://localhost:8080/callback` and pass `--redirect-uri http://localhost:8080/callback` to the login script in step 6. Some app configs require https — if so, tell me and I'll switch the helper to the paste-the-URL flow instead.

✅ Checkpoint: `http://127.0.0.1:8080/callback` is registered.

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
2. TikTok redirects to `http://127.0.0.1:8080/callback`; the helper catches it.
3. It exchanges the code and writes **`tiktok_token.json`** (access + refresh token).

If the browser didn't open, copy the printed URL manually. If you registered a different redirect URI, run:

```bash
python3 scripts/tiktok_login.py --redirect-uri http://localhost:8080/callback
```

✅ Checkpoint: `tiktok_token.json` exists and the script printed `scope: video.upload`.

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
| `scope_not_authorized` / upload rejected    | `video.upload` not enabled, or you're not a Sandbox test user (steps 2, 5)                 |
| Token refresh fails                         | Refresh token expired → re-run the login helper                                            |
| `unaudited_client_can_only_post_to_private` | Direct mode only — expected until audit; keep `privacy_level: SELF_ONLY` or use inbox mode |

## Notes / limits

- **Inbox mode = one manual tap** to publish (by design, no audit).
- Tokens: access token ~24h, refresh token ~365d; the app refreshes automatically using `tiktok_token.json`.
- Video must be a real MP4 (the pipeline's `build_reel` output is fine); single-page comics still become a short reel.
