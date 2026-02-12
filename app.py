import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64
import hashlib

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?output=csv"
PASSWORD = "888"
SITE_URL = "https://swd-case.streamlit.app" 

# === 2. 核心技術函數 ===
def generate_id(link):
    return hashlib.md5(str(link).encode()).hexdigest()[:10]

@st.cache_data(ttl=120)
def get_audio_base64(url):
    if not isinstance(url, str) or url == "": return None
    target_url = url.split('?')[0] + "?download=1" if "sharepoint.com" in url else url
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(target_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            b64 = base64.b64encode(resp.content).decode('utf-8')
            return f"data:audio/mpeg;base64,{b64}"
    except: return None
    return None

def get_embed_url(link):
    if "drive.google.com" in link and "/view" in link:
        return link.replace("/view", "/preview")
    return link

# === 3. 資料載入 (微調：允許顯示圖檔，但排除資料夾) ===
@st.cache_data(ttl=180)
def load_data():
    try:
        df = pd.read_csv(CSV_URL, on_bad_lines='skip', engine='python')
        df.columns = [str(c).strip().lower() for c in df.columns]
        for col in ['title', 'link', 'category', 'type', 'short']:
            if col not in df.columns: df[col] = ""
        df = df.fillna("")
        
        # 顯示名稱補強
        df['short'] = df.apply(lambda r: r['short'] if str(r['short']).strip() != "" else r['title'], axis=1)
        
        # 排除「案例資料庫」
        df = df[~df['category'].astype(str).str.contains("案例資料庫", na=False)]
        # 排除 Google Drive / SharePoint 的「資料夾」連結 (因為無法直接播放/顯示)
        df = df[~df['link'].astype(str).str.contains('/folders/')]
        
        df['uid'] = df['link'].apply(generate_id)
        return df.reset_index(drop=True)
    except: return pd.DataFrame()

# === 4. UI 元件 ===
def render_copy_ui(label, text_to_copy, is_disabled=False, warning_msg=""):
    if is_disabled:
        html_code = f"""<div style="background-color:#fff5f5;padding:12px;border-radius:8px;border:1px solid #feb2b2;margin-bottom:10px;"><label style="font-size:12px;color:#c53030;font-weight:bold;">{label}</label><p style="font-size:13px;color:#333;margin:8px 0;">⚠️ {warning_msg}</p></div>"""
    else:
        html_code = f"""<div style="background-color:#f8f9fa;padding:10px;border-radius:8px;border:1px solid #eee;margin-bottom:10px;"><label style="font-size:12px;color:#666;">{label}</label><input type="text" value="{text_to_copy}" id="copyInput" readonly style="width:100%;padding:8px;margin:5px 0;border:1px solid #ddd;border-radius:4px;"><button onclick="copyToClipboard()" style="width:100%;padding:10px;background:#0097DA;color:white;border:none;border-radius:5px;cursor:pointer;font-weight:bold;">📋 複製網址</button><script>function copyToClipboard(){{var copyText=document.getElementById("copyInput");copyText.select();navigator.clipboard.writeText(copyText.value).then(function(){{alert("✅ 複製成功！");}});}}</script></div>"""
    components.html(html_code, height=150)

@st.dialog("🔗 分享檔案權限")
def show_share_dialog(display_name, link, uid, is_video=False, is_image=False):
    st.write(f"📄 **{display_name}**")
    render_copy_ui("🏢 內部分享連結 (同仁下載用)", link)
    if is_video:
        render_copy_ui("🌏 外部分享連結", "", is_disabled=True, warning_msg="影片涉及『客戶版權』及『全家便利商店場域』，不提供對外分享。")
    elif is_image:
        render_copy_ui("🌏 外部分享連結", "", is_disabled=True, warning_msg="此為『圖片檔』，涉及版權保護，不提供對外分享。")
    else:
        share_link = f"{SITE_URL}?id={uid}"
        render_copy_ui("🌏 外部分享連結 (客戶試聽/防下載)", share_link)

# === 5. 主程式 ===
def main():
    # 1. 頁面基本設定 (必須在最上方)
    st.set_page_config(page_title="全家通路媒體資料庫", layout="centered")
    
    # 2. 初始化 Session State
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'display_count' not in st.session_state:
        st.session_state.display_count = 20

    df = load_data()
    if df.empty:
        st.error("資料載入失敗，請檢查網路。")
        return

    # 3. 檢查網址參數 (客戶模式)
    params = st.query_params
    target_uid = params.get("id", None)

    if target_uid:
        # --- 進入客戶模式 (不需登入，由 UID 驅動) ---
        target_row = df[df['uid'] == target_uid]
        if not target_row.empty:
            item = target_row.iloc[0]
            # (這裡放您原本的客戶模式顯示邏輯...)
            st.subheader(f"🎵 作品預覽：{item['short']}")
            # ...
            if st.button("🏠 回到首頁"):
                st.query_params.clear()
                st.rerun()
            return # 客戶模式執行完後直接結束
    
    # 4. 內部模式：登入檢查 (只有在沒有 target_uid 時才會走到這)
    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align: center;'>🔒 全家通路媒體資料庫</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            pw = st.text_input("請輸入內部資料庫密碼", type="password")
            if st.form_submit_button("解鎖系統", use_container_width=True):
                if pw == PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("密碼錯誤")
        return # 沒登入就結束，不顯示下方搜尋介面

    # 5. 搜尋與列表渲染 (登入後可見)
    # ... (原本的搜尋、過濾、展開更多邏輯)

    # B. 內部模式
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        with st.form("login"):
            pw = st.text_input("密碼", type="password")
            if st.form_submit_button("登入"):
                if pw == PASSWORD: st.session_state.logged_in = True; st.rerun()
        return

    # 搜尋與過濾
    search_query = st.text_input("🔍 關鍵字搜尋")
    if 'last_search' not in st.session_state or st.session_state.last_search != search_query:
        st.session_state.display_count = 20
        st.session_state.last_search = search_query

    c1, c2 = st.columns(2)
    with c1:
        cat_list = sorted([str(x) for x in df['category'].unique() if str(x).strip()])
        sel_cat = st.selectbox("📂 分類", ["全部"] + cat_list)
    with c2:
        type_filter = st.radio("📑 類型", ["全部", "企頻", "新鮮視", "側帶"], horizontal=True)

    mask = pd.Series([True] * len(df), index=df.index)
    if search_query:
        mask &= (df['title'].str.contains(search_query, case=False) | df['category'].str.contains(search_query, case=False))
    if sel_cat != "全部": mask &= (df['category'] == sel_cat)
    if type_filter != "全部":
        mask &= (df['type'].str.contains(type_filter, case=False) | df['title'].str.contains(type_filter, case=False))

    results = df[mask]
    total_results = len(results)
    
    current_results = results.head(st.session_state.display_count)
    for _, row in current_results.iterrows():
        uid = row['uid']
        display_name = row['short']
        t_low = str(row['title']).lower()
        tp_low = str(row['type']).lower()
        
        # 類型判定
        is_audio = any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in tp_low
        is_video = any(x in tp_low for x in ["新鮮視", "側帶"]) or any(ext in t_low for ext in ['.mp4', '.mov'])
        is_image = any(ext in t_low for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])

        with st.expander(f"📄 {display_name}"):
            if is_audio:
                if st.button("▶️ 載入音訊", key=f"p_{uid}"):
                    b64 = get_audio_base64(row['link'])
                    if b64: st.audio(b64)
            elif is_video:
                st.info("📺 影片預覽：限同仁點擊下方『開啟檔案』觀看。")
            elif is_image:
                st.warning("🖼️ 此為『圖片檔』，不是『影像檔』。同仁請點擊下方『開啟檔案』查看。")
            else:
                components.iframe(get_embed_url(row['link']), height=400)
            
            bt1, bt2 = st.columns(2)
            with bt1: st.link_button("↗ 開啟檔案", row['link'], use_container_width=True)
            with bt2:
                if st.button("🔗 分享", key=f"s_{uid}", use_container_width=True):
                    show_share_dialog(display_name, row['link'], uid, is_video=is_video, is_image=is_image)

    # 展開更多
    if total_results > st.session_state.display_count:
        if st.button(f"🔽 展開更多案例 (目前 {st.session_state.display_count}/{total_results})", use_container_width=True):
            st.session_state.display_count += 20
            st.rerun()
