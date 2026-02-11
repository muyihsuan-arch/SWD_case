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
SITE_URL = "https://swd-case.streamlit.app" 

# === 2. 核心技術函數 ===
def generate_id(link):
    """利用連結產生唯一 ID"""
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
        # 排除「案例資料庫」標籤
        df = df[~df['category'].astype(str).str.contains("案例資料庫", na=False)]
        # 排除圖片與特定資料夾
        img_ext = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        df = df[~df['title'].astype(str).str.lower().str.endswith(img_ext)]
        df = df[~df['link'].astype(str).str.contains('/folders/')]
        df['uid'] = df['link'].apply(generate_id)
        return df.reset_index(drop=True)
    except: return pd.DataFrame()

# === 4. 分享 UI 與 警語設計 ===
def render_copy_ui(label, text_to_copy, is_disabled=False, warning_msg=""):
    """
    若 is_disabled 為 True，則不顯示複製按鈕，顯示警告文字
    """
    if is_disabled:
        html_code = f"""
        <div style="background-color: #fff5f5; padding: 15px; border-radius: 8px; border: 1px solid #feb2b2; margin-bottom:10px;">
            <label style="font-size:12px; color:#c53030; font-weight:bold;">{label}</label>
            <p style="font-size:14px; color:#333; margin: 10px 0; line-height:1.5;">⚠️ {warning_msg}</p>
        </div>
        """
    else:
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
    components.html(html_code, height=140)

@st.dialog("🔗 分享檔案權限")
def show_share_dialog(title, link, uid, is_video=False):
    st.write(f"📄 **{title}**")
    # 內部分享：永遠可用
    render_copy_ui("🏢 內部分享連結 (同仁下載用)", link)
    
    # 外部分享：依類型判定
    if is_video:
        render_copy_ui("🌏 外部分享連結", "", is_disabled=True, 
                       warning_msg="影片涉及『客戶版權』或『全家便利商店場域』，不提供對外分享。")
    else:
        share_link = f"{SITE_URL}?id={uid}"
        render_copy_ui("🌏 外部分享連結 (客戶試聽/防下載)", share_link)

# === 5. 主程式 ===
def main():
    st.set_page_config(page_title="全家通路媒體資料庫", layout="centered")

    df = load_data()
    if df.empty: return

    # A. 客戶預覽模式 (維持音訊預覽)
    params = st.query_params
    target_uid = params.get("id", None)
    if target_uid:
        target_row = df[df['uid'] == target_uid]
        if not target_row.empty:
            item = target_row.iloc[0]
            # 再次檢查，若客戶繞過 ID 進來看影片，則不顯示
            if "新鮮視" in str(item['type']) or "側帶" in str(item['type']):
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

    # 搜尋與列表
    search_query = st.text_input("🔍 關鍵字搜尋")
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
    for i, row in results.iterrows():
        uid = row['uid']
        # 判定是否為影片
        is_video = any(x in str(row['type']) for x in ["新鮮視", "側帶"])
        
        with st.expander(f"📄 {row['title']}"):
            if any(ext in str(row['title']).lower() for ext in ['.mp3', '.wav', '.m4a']):
                if st.button("▶️ 載入音訊", key=f"p_{uid}"):
                    b64 = get_audio_base64(row['link'])
                    if b64: st.audio(b64)
            elif is_video:
                st.info("📺 內部預覽：影片僅限同仁點擊下方『直接開啟』觀看。")
            else:
                components.iframe(get_embed_url(row['link']), height=400)

            c1, c2 = st.columns(2)
            with c1: st.link_button("↗ 直接開啟 (SharePoint)", row['link'], use_container_width=True)
            with c2:
                if st.button("🔗 分享檔案", key=f"s_{uid}", use_container_width=True):
                    show_share_dialog(row['title'], row['link'], uid, is_video=is_video)

if __name__ == "__main__":
    main()
