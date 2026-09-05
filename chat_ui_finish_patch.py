from __future__ import annotations


FINAL_UI_PATCH = r'''<script>
// Keep Google OAuth out of the active UI until the Supabase provider is
// actually enabled. This lets the team defer Google Cloud setup without
// leaving a broken button in production. Once the provider is enabled, the
// button appears automatically on the next page load.
(()=>{
  const google=document.querySelector('#googleAuthBtn');
  const divider=document.querySelector('.auth-divider');
  if(!google) return;

  google.hidden=true;
  google.style.display='none';
  if(divider){divider.hidden=true;divider.style.display='none';}

  const cfg=window.CHAT_CONFIG||{};
  if(!cfg.supabaseUrl||!cfg.supabaseAnonKey) return;

  const settingsUrl=String(cfg.supabaseUrl).replace(/\/$/,'')+'/auth/v1/settings';
  fetch(settingsUrl,{headers:{apikey:cfg.supabaseAnonKey}})
    .then(r=>r.ok?r.json():null)
    .then(data=>{
      if(data?.external?.google===true){
        google.hidden=false;
        google.style.display='flex';
        if(divider){divider.hidden=false;divider.style.display='flex';}
      }
    })
    .catch(()=>{});
})();
</script>'''


def inject_final_ui_patch(html: str) -> str:
    return html.replace("</body>", FINAL_UI_PATCH + "\n</body>", 1)
