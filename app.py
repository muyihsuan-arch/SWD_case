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

# === 3. 資料載入 ===
@st.cache_data(ttl=180)
def load_data():
    try:
        df = pd.read_csv(CSV_URL, on_bad_lines='skip', engine='python')
        df.columns = [str(c).strip().lower() for c in df.columns]
        for col in ['title', 'link', 'category', 'type']:
            if col not in df.columns: df[col] = ""
        df = df.fillna("")
        df = df[~df['category'].astype(str).str.contains("案例資料庫", na=False)]
        img_ext = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        df = df[~df['title'].astype(str).str.lower().str.endswith(img_ext)]
        df = df[~df['link'].astype(str).str.contains('/folders/')]
        df['uid'] = df['link'].apply(generate_id)
        return df.reset_index(drop=True)
    except: return pd.DataFrame()

# === 4. UI 元件 ===
def render_copy_ui(label, text_to_copy, is_disabled=False, warning_msg=""):
    if is_disabled:
        html_code = f"""
        <div style="background-color: #fff5f5; padding: 12px; border-radius: 8px; border: 1px solid #feb2b2; margin-bottom:10px;">
            <label style="font-size:12px; color:#c53030; font-weight:bold;">{label}</label>
            <p style="font-size:13px; color:#333; margin: 8px 0;">⚠️ {warning_msg}</p>
        </div>
        """
    else:
        html_code = f"""
        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #eee; margin-bottom:10px;">
            <label style="font-size:12px; color:#666;">{label}</label>
            <input type="text" value="{text_to_copy}" id="copyInput" readonly style="width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px;">
            <button onclick="copyToClipboard()" style="width: 100%; padding: 10px; background: #0097DA; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">📋 複製網址</button>
            <script>
                function copyToClipboard() {{
                    var copyText = document.getElementById("copyInput");
                    copyText.select();
                    navigator.clipboard.writeText(copyText.value).then(function() {{ alert("✅ 複製成功！"); }});
                }}
            </script>
        </div>
        """
    components.html(html_code, height=150)

@st.dialog("🔗 分享檔案權限")
def show_share_dialog(title, link, uid, is_video=False):
    st.write(f"📄 **{title}**")
    render_copy_ui("🏢 內部分享連結 (同仁下載用)", link)
    if is_video:
        render_copy_ui("🌏 外部分享連結", "", is_disabled=True, warning_msg="影片涉及『客戶版權』或『全家便利商店場域』，不提供對外分享。")
    else:
        share_link = f"{SITE_URL}?id={uid}"
        render_copy_ui("🌏 外部分享連結 (客戶試聽/防下載)", share_link)

# === 5. 主程式 ===
def main():
    st.set_page_config(page_title="全家通路媒體資料庫", layout="centered")
    
    # 初始化顯示筆數
    if 'display_count' not in st.session_state:
        st.session_state.display_count = 20

    df = load_data()
    if df.empty: return

    # A. 客戶模式
    params = st.query_params
    target_uid = params.get("id", None)
    if target_uid:
        target_row = df[df['uid'] == target_uid]
        if not target_row.empty:
            item = target_row.iloc[0]
            if any(x in str(item['type']) for x in ["新鮮視", "側帶"]):
                st.error("此檔案涉及版權保護，不開放對外預覽。")
                return
            st.subheader(f"🎵 作品預覽：{item['title']}")
            b64 = get_audio_base64(item['link'])
            if b64: st.markdown(f'<audio controls controlsList="nodownload" style="width:100%;"><source src="{b64}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
            if st.button("🏠 回到首頁"): st.query_params.clear(); st.rerun()
            return

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
    # 當搜尋字串改變時，重置顯示筆數
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
    
    # 渲染結果
    current_results = results.head(st.session_state.display_count)
    for _, row in current_results.iterrows():
        uid = row['uid']
        is_video = any(x in str(row['type']) for x in ["新鮮視", "側帶"])
        with st.expander(f"📄 {row['title']}"):
            if any(ext in str(row['title']).lower() for ext in ['.mp3', '.wav', '.m4a']):
                if st.button("▶️ 播放音訊", key=f"p_{uid}"):
                    b64 = get_audio_base64(row['link'])
                    if b64: st.audio(b64)
            elif is_video:
                st.info("📺 影片權限：限同仁觀看。")
            else:
                components.iframe(get_embed_url(row['link']), height=400)
            
            bt1, bt2 = st.columns(2)
            with bt1: st.link_button("↗ 開啟檔案", row['link'], use_container_width=True)
            with bt2:
                if st.button("🔗 分享", key=f"s_{uid}", use_container_width=True):
                    show_share_dialog(row['title'], row['link'], uid, is_video=is_video)

    # 「展開更多」按鈕邏輯
    if total_results > st.session_state.display_count:
        st.write(f"目前顯示 {st.session_state.display_count} 筆 / 共 {total_results} 筆")
        if st.button("🔽 展開更多案例 (20筆)", use_container_width=True):
            st.session_state.display_count += 20
            st.rerun()
    elif total_results > 0:
        st.write(f"✨ 已顯示全部 {total_results} 筆結果")

if __name__ == "__main__":
    main()
