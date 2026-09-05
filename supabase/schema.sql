-- Run this once in Supabase SQL Editor.
-- It creates persistent per-user chat history with row-level security.

create extension if not exists pgcrypto;

create table if not exists public.conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null default 'แชทใหม่',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.conversations(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    role text not null check (role in ('user','assistant','system')),
    content text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists conversations_user_updated_idx
    on public.conversations(user_id, updated_at desc);

create index if not exists messages_conversation_created_idx
    on public.messages(conversation_id, created_at asc);

create or replace function public.touch_conversation_updated_at()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    update public.conversations
    set updated_at = now()
    where id = new.conversation_id;
    return new;
end;
$$;

drop trigger if exists messages_touch_conversation on public.messages;
create trigger messages_touch_conversation
after insert on public.messages
for each row execute function public.touch_conversation_updated_at();

alter table public.conversations enable row level security;
alter table public.messages enable row level security;

-- Conversations: only the authenticated owner can see or modify them.
drop policy if exists conversations_select_own on public.conversations;
create policy conversations_select_own
on public.conversations for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists conversations_insert_own on public.conversations;
create policy conversations_insert_own
on public.conversations for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists conversations_update_own on public.conversations;
create policy conversations_update_own
on public.conversations for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists conversations_delete_own on public.conversations;
create policy conversations_delete_own
on public.conversations for delete
to authenticated
using (auth.uid() = user_id);

-- Messages: user_id is repeated intentionally so RLS stays simple and fast.
drop policy if exists messages_select_own on public.messages;
create policy messages_select_own
on public.messages for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists messages_insert_own on public.messages;
create policy messages_insert_own
on public.messages for insert
to authenticated
with check (
    auth.uid() = user_id
    and exists (
        select 1
        from public.conversations c
        where c.id = conversation_id
          and c.user_id = auth.uid()
    )
);

drop policy if exists messages_delete_own on public.messages;
create policy messages_delete_own
on public.messages for delete
to authenticated
using (auth.uid() = user_id);

grant usage on schema public to authenticated;
grant select, insert, update, delete on public.conversations to authenticated;
grant select, insert, delete on public.messages to authenticated;
