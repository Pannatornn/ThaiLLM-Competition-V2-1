from chat_ui import render_chat_ui
from chat_ui_finish_patch import inject_final_ui_patch
from chat_ui_patch import inject_chat_runtime_patch


def test_google_oauth_button_is_hidden_until_provider_is_enabled():
    html = inject_final_ui_patch(inject_chat_runtime_patch(render_chat_ui({})))
    assert "Continue with Google" in html
    assert "/auth/v1/settings" in html
    assert "data?.external?.google===true" in html
    assert "google.style.display='none'" in html
    assert "google.style.display='flex'" in html


def test_english_first_legacy_theme_stays_active():
    html = inject_chat_runtime_patch(render_chat_ui({}))
    assert '<html lang="en">' in html
    assert "New chat" in html
    assert "Search chats" in html
    assert "Competition tools" in html
    assert "legacyChatTheme" in html
    assert "#07101d" in html
    assert "#6366f1" in html
    assert "#14b8a6" in html
