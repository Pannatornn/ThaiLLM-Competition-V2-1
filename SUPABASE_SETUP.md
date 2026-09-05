# Supabase setup for persistent chat history

The ChatGPT-style UI works in guest mode without Supabase, but guest history is stored only in the browser. To let users sign in and reopen chats on any device, configure Supabase.

## 1. Create the chat-history schema

Run the complete contents of:

```text
supabase/schema.sql
```

This creates `conversations`, `messages`, indexes, and Row Level Security policies so users can only access their own chats.

## 2. Email/password authentication

In Supabase:

**Authentication → Providers → Email**

Enable Email/Password. Email confirmation can stay on for production or be disabled temporarily for a competition demo.

## 3. Google sign-in

The web UI includes **Continue with Google** and calls Supabase `signInWithOAuth({ provider: 'google' })`.

Google still requires OAuth credentials owned by the project team; never commit the client secret to GitHub.

### Google Cloud Auth Platform

Create an OAuth client with application type **Web application**.

Use this production origin:

```text
https://thaillm-competition-v2-1.onrender.com
```

Use this authorized redirect URI:

```text
https://neonezhgtdkowvedfxvb.supabase.co/auth/v1/callback
```

Required scopes are the standard profile scopes used by Supabase Auth:

```text
openid
email
profile
```

### Supabase Google provider

Open:

**Authentication → Providers → Google**

Enable Google and paste the Google OAuth **Client ID** and **Client Secret** there.

Then open:

**Authentication → URL Configuration**

Set the Site URL to:

```text
https://thaillm-competition-v2-1.onrender.com
```

Add this Redirect URL:

```text
https://thaillm-competition-v2-1.onrender.com/
```

After that, **Continue with Google** creates/signs in the Supabase user and the same `conversations` / `messages` RLS rules apply automatically.

## 4. Render environment variables

The production Render service uses:

```text
SUPABASE_URL=https://neonezhgtdkowvedfxvb.supabase.co
SUPABASE_ANON_KEY=<Supabase publishable key>
```

`SUPABASE_ANON_KEY` / the publishable key is a browser credential. Security comes from RLS. Never put the Supabase `service_role` key or Google client secret in the browser or repository.

Existing ThaiLLM environment variables remain unchanged.

## 5. Deploy

The Render start command is:

```text
uvicorn render_chat_app:app --host 0.0.0.0 --port $PORT
```

After deployment:

1. Open the site.
2. Click the account area in the bottom-left.
3. Sign in with Google or email/password.
4. Start a chat.
5. Refresh or sign in from another browser/device to confirm the same conversation history appears.

## Behavior without Supabase

If `SUPABASE_URL` or `SUPABASE_ANON_KEY` is missing, the UI automatically runs in guest mode using browser `localStorage`. Q&A, question-file upload, batch run, and ThaiLLM API-key session override still work.
