# Supabase setup for persistent chat history

The ChatGPT-style UI works in guest mode without Supabase, but guest history is stored only in the browser. To let users sign in and reopen chats on any device, configure Supabase.

## 1. Create a Supabase project

Create a project at Supabase and open **SQL Editor**.

Run the complete contents of:

```text
supabase/schema.sql
```

This creates:

- `conversations`
- `messages`
- indexes
- an `updated_at` trigger
- Row Level Security policies so users can only access their own chats

## 2. Enable email/password authentication

In Supabase:

**Authentication → Providers → Email**

Enable Email/Password. You can keep email confirmation on for production, or turn it off temporarily for a hackathon demo.

## 3. Add Render environment variables

Add these to the Render service:

```text
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_KEY
```

`SUPABASE_ANON_KEY` is a public browser credential. Security comes from the RLS policies in `supabase/schema.sql`. Never put the Supabase service-role key in the browser or repository.

Existing ThaiLLM environment variables remain unchanged.

## 4. Deploy

The Render start command should be:

```text
uvicorn render_chat_app:app --host 0.0.0.0 --port $PORT
```

After deployment:

1. Open the site.
2. Click the user area at bottom-left.
3. Create an account or sign in.
4. Start a chat.
5. Refresh or sign in from another browser/device to confirm the same conversation history appears.

## Behavior without Supabase

If `SUPABASE_URL` or `SUPABASE_ANON_KEY` is missing, the UI automatically runs in guest mode using browser `localStorage`. Q&A, question-file upload, batch run, and ThaiLLM API-key session override still work.
