import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from chat_ui import render_chat_ui
from chat_ui_patch import inject_chat_runtime_patch
from render_chat_app import _recent_user_programs


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


def test_chat_runtime_patch_enables_contextual_endpoint():
    html = inject_chat_runtime_patch(render_chat_ui({}))
    assert "'/api/chat'" in html
    assert "messages=[...(c.messages||[])]" in html
    assert "contextualized" in html


def test_recent_user_program_context_ignores_assistant_mentions():
    history = [
        {"role": "user", "content": "AIT เรียนกี่หน่วยกิต?"},
        {
            "role": "assistant",
            "content": "AIT มี 120 หน่วยกิต ส่วน DSBA, IT และ IT International เป็นหลักสูตรอื่น",
        },
    ]
    assert _recent_user_programs(history) == ["AIT"]


def test_recent_user_program_context_supports_comparison_pair():
    history = [
        {"role": "user", "content": "AIT กับ DSBA ต่างกันอย่างไร"},
        {"role": "assistant", "content": "ทั้งสองหลักสูตรมีจุดเน้นต่างกัน"},
    ]
    assert set(_recent_user_programs(history)) == {"AIT", "DSBA"}


def test_supabase_schema_has_rls_for_private_history():
    sql = (ROOT / "supabase/schema.sql").read_text(encoding="utf-8").casefold()
    assert "create table if not exists public.conversations" in sql
    assert "create table if not exists public.messages" in sql
    assert "enable row level security" in sql
    assert "auth.uid() = user_id" in sql
    assert "on delete cascade" in sql
