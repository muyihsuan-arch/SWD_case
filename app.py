import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64
import hashlib
import time

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?output=csv"
PASSWORD = "888"
# 請務必更換為妳部署後的網址
SITE_URL = "https://swd-case.streamlit.app" 

# === 2. 核心技術函數 ===
def generate_id(link):
    return hashlib.md5(str(link).encode()).hexdigest()[:10]

@st.cache_data(ttl=300)
def get_audio_base64(url):
    if not isinstance(url, str) or url == "": return None
    target_url = url.split('?')[0] + "?download=1" if "sharepoint.com" in url else url
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(target_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            b64 = base64.b64encode(resp.content).decode('utf-8')
            return f"data:audio/mpeg;base64,{b64}"
    except: return None
    return None

def get_embed_url(link):
    """針對不同來源轉換為嵌入預覽格式"""
    if "sharepoint.com" in link:
        # 將 SharePoint 連結轉為嵌入模式，通常能隱藏部分原生介面
        return link.replace("view.aspx", "embedview.aspx")
    if "drive.google.com" in link and "/view" in link:
        return link.replace("/view", "/preview")
    return link

# === 3. 資料載入 (過濾案例資料庫) ===
@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = [str(c).strip().lower() for c in df.columns]
        for col in ['title', 'link', 'category', 'type']:
            if col not in df.columns: df[col] = ""
        df = df.fillna("")
        # 排除「案例資料庫」與特定格式
        df = df[~df['category'].astype(str).str.contains("案例資料庫", na=False)]
        img_ext = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        df = df[~df['title'].astype(str).str.lower().str.endswith(img_ext)]
        df = df[~df['link'].astype(str).str.contains('/folders/')]
        df['uid'] = df['link'].apply(generate_id)
        return df.reset_index(drop=True)
    except: return pd.DataFrame()

# === 4. 彈窗與分享 UI ===
def render_copy_ui(label, text_to_copy):
    html_code = f"""
    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #eee; margin-bottom:10px;">
        <label style="font-size:12px; color:#666;">{label}</label>
        <input type="text" value="{text_to_copy}" id="copyInput" readonly style="width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px;">
        <button onclick="copyToClipboard()" style="width: 100%; padding: 8px; background: #0097DA; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">📋 複製網址</button>
        <script>
            function copyToClipboard() {{
                var copyText = document.getElementById("copyInput");
                copyText.select();
                navigator.clipboard.writeText(copyText.value).then(function() {{ alert("✅ 複製成功！"); }});
            }}
        </script>
    </div>
    """
    components.html(html_code, height=130)

@st.dialog("🔗 分享檔案")
def show_share_dialog(title, link, uid):
    st.write(f"📄 **{title}**")
    render_copy_ui("🏢 內部分享連結 (同仁下載用)", link)
    share_link = f"{SITE_URL}?id={uid}"
    render_copy_ui("🌏 外部分享連結 (客戶試聽/防下載)", share_link)

# === 5. 主程式 ===
def main():
    st.set_page_config(page_title="全家通路媒體資料庫", layout="centered")

    # 版權保護 CSS：隱藏下載與右鍵選單
    st.markdown("""
        <style>
            audio::-webkit-media-controls-enclosure { overflow: hidden; }
            audio::-webkit-media-controls-panel { width: calc(100% + 30px); }
            /* 針對嵌入視窗的遮蓋邏輯 */
            iframe { border: none; border-radius: 8px; }
        </style>
    """, unsafe_allow_html=True)

    df = load_data()
    if df.empty: return

    params = st.query_params
    target_uid = params.get("id", None)

    # --- A. 客戶預覽模式 (版權保護最優先) ---
    if target_uid:
        target_row = df[df['uid'] == target_uid]
        if not target_row.empty:
            item = target_row.iloc[0]
            st.subheader(f"🎵 作品預覽：{item['title']}")
            st.warning("⚠️ 版權所有，僅供線上試聽，禁止下載。")
            
            t_low = str(item['title']).lower()
            tp_low = str(item['type']).lower()

            if any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in tp_low:
                b64 = get_audio_base64(item['link'])
                if b64:
                    st.markdown(f'<audio controls controlsList="nodownload" style="width:100%;"><source src="{b64}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
            else:
                # 影片類：客戶模式下強制嵌入，不給跳轉按鈕
                embed_url = get_embed_url(item['link'])
                components.iframe(embed_url, height=500)
            
            st.divider()
            if st.button("🏠 回到首頁"):
                st.query_params.clear()
                st.rerun()
            return

    # --- B. 內部模式 ---
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align: center;'>🔒 全家通路媒體資料庫</h2>", unsafe_allow_html=True)
        with st.form("login"):
            pw = st.text_input("密碼", type="password")
            if st.form_submit_button("解鎖", use_container_width=True):
                if pw == PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("密碼錯誤")
        return

    # 搜尋 UI
    search_query = st.text_input("🔍 搜尋關鍵字")
    c1, c2 = st.columns(2)
    with c1:
        cat_list = sorted([str(x) for x in df['category'].unique() if str(x).strip()])
        sel_cat = st.selectbox("📂 分類", ["全部"] + cat_list)
    with c2:
        type_filter = st.radio("📑 類型", ["全部", "企頻", "新鮮視", "側帶"], horizontal=True)

    # 篩選邏輯
    mask = pd.Series([True] * len(df), index=df.index)
    if search_query:
        mask &= (df['title'].str.contains(search_query, case=False) | df['category'].str.contains(search_query, case=False))
    if sel_cat != "全部":
        mask &= (df['category'] == sel_cat)
    if type_filter != "全部":
        mask &= (df['type'].str.contains(type_filter, case=False) | df['title'].str.contains(type_filter, case=False))

    results = df[mask]
    for _, row in results.iterrows():
        uid = row['uid']
        with st.expander(f"📄 {row['title']}"):
            t_low, tp_low = str(row['title']).lower(), str(row['type']).lower()
            
            if any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in tp_low:
                if st.button("▶️ 播放音訊", key=f"p_{uid}"):
                    b64 = get_audio_base64(row['link'])
                    if b64: st.audio(b64)
            elif any(ext in t_low for ext in ['.mp4', '.mov']) or "新鮮視" in tp_low:
                # 內部同仁：給按鈕跳轉方便工作
                st.info("📺 影片建議跳轉開啟較流暢")
                st.link_button("🎬 開啟影片 (跳轉)", row['link'], use_container_width=True)
            else:
                components.iframe(get_embed_url(row['link']), height=400)

            c1, c2 = st.columns(2)
            with c1: st.link_button("↗ SharePoint", row['link'], use_container_width=True)
            with c2:
                if st.button("🔗 分享連結", key=f"s_{uid}", use_container_width=True):
                    show_share_dialog(row['title'], row['link'], uid)

if __name__ == "__main__":
    main()
