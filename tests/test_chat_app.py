from pathlib import Path

from chat_ui import render_chat_ui


ROOT = Path(__file__).resolve().parents[1]


def test_chat_ui_contains_history_auth_and_chat_controls():
    html = render_chat_ui(
        {
            "supabaseUrl": "https://example.supabase.co",
            "supabaseAnonKey": "public-anon-key",
            "authConfigured": True,
            "modelDisplay": "OpenThaiGPT-ThaiLLM-8B-Instruct-v7.2",
        }
    )
    assert "แชทใหม่" in html
    assert "ค้นหาแชท" in html
    assert "Sign in" in html
    assert "Create account" in html
    assert "conversationTitle" in html
    assert "messages" in html
    assert "question,answer" in html
    assert "__CHAT_CONFIG__" not in html


def test_supabase_schema_has_rls_for_private_history():
    sql = (ROOT / "supabase/schema.sql").read_text(encoding="utf-8").casefold()
    assert "create table if not exists public.conversations" in sql
    assert "create table if not exists public.messages" in sql
    assert "enable row level security" in sql
    assert "auth.uid() = user_id" in sql
    assert "on delete cascade" in sql
