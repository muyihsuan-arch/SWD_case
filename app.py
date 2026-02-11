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

@st.cache_data(ttl=120) # 縮短快取時間至 2 分鐘，釋放記憶體壓力
def get_audio_base64(url):
    if not isinstance(url, str) or url == "": return None
    target_url = url.split('?')[0] + "?download=1" if "sharepoint.com" in url else url
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # 增加 timeout 避免網路卡死導致 App 掛掉
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

# === 3. 資料載入 (強化防錯與排除邏輯) ===
@st.cache_data(ttl=180) # 每 3 分鐘自動更新一次資料
def load_data():
    try:
        # 使用 engine='python' 提高讀取穩定性，跳過損壞行
        df = pd.read_csv(CSV_URL, on_bad_lines='skip', engine='python')
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        for col in ['title', 'link', 'category', 'type']:
            if col not in df.columns: df[col] = ""
        
        df = df.fillna("")
        # 排除「案例資料庫」與非必要檔案
        df = df[~df['category'].astype(str).str.contains("案例資料庫", na=False)]
        img_ext = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tif')
        df = df[~df['title'].astype(str).str.lower().str.endswith(img_ext)]
        df = df[~df['link'].astype(str).str.contains('/folders/')]
        
        df['uid'] = df['link'].apply(generate_id)
        return df.reset_index(drop=True)
    except Exception as e:
        return pd.DataFrame()

# === 4. 分享 UI 與 警語設計 ===
def render_copy_ui(label, text_to_copy, is_disabled=False, warning_msg=""):
    if is_disabled:
        html_code = f"""
        <div style="background-color: #fff5f5; padding: 12px; border-radius: 8px; border: 1px solid #feb2b2; margin-bottom:10px;">
            <label style="font-size:12px; color:#c53030; font-weight:bold;">{label}</label>
            <p style="font-size:13px; color:#333; margin: 8px 0; line-height:1.4;">⚠️ {warning_msg}</p>
        </div>
        """
    else:
        html_code = f"""
        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #eee; margin-bottom:10px;">
            <label style="font-size:12px; color:#666;">{label}</label>
            <input type="text" value="{text_to_copy}" id="copyInput" readonly style="width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; font-size:14px;">
            <button onclick="copyToClipboard()" style="width: 100%; padding: 10px; background: #0097DA; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">📋 點此複製網址</button>
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
        render_copy_ui("🌏 外部分享連結", "", is_disabled=True, 
                       warning_msg="影片涉及『客戶版權』及『全家便利商店場域』，不提供對外分享。")
    else:
        share_link = f"{SITE_URL}?id={uid}"
        render_copy_ui("🌏 外部分享連結 (客戶試聽/防下載)", share_link)

# === 5. 主程式 ===
def main():
    st.set_page_config(page_title="全家通路媒體資料庫", layout="centered")

    # 隱藏下載與記憶體優化樣式
    st.markdown("<style>audio::-webkit-media-controls-enclosure { overflow: hidden; }</style>", unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.error("目前無法載入資料庫，請檢查網路連線或稍後再試。")
        return

    # A. 客戶預覽模式 (UID 比對)
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
        with st.form("login_form"):
            st.markdown("### 🔒 內部員工登入")
            pw = st.text_input("請輸入資料庫密碼", type="password")
            if st.form_submit_button("登入系統", use_container_width=True):
                if pw == PASSWORD: st.session_state.logged_in = True; st.rerun()
                else: st.error("密碼錯誤")
        return

    # 搜尋與篩選介面
    search_query = st.text_input("🔍 關鍵字搜尋 (品牌、產品、內容)", placeholder="例如：全家、咖啡...")
    c1, c2 = st.columns(2)
    with c1:
        cat_list = sorted([str(x) for x in df['category'].unique() if str(x).strip()])
        sel_cat = st.selectbox("📂 分類過濾", ["全部顯示"] + cat_list)
    with c2:
        type_filter = st.radio("📑 類型過濾", ["全部", "企頻", "新鮮視", "側帶"], horizontal=True)

    # 安全篩選邏輯
    mask = pd.Series([True] * len(df), index=df.index)
    if search_query:
        mask &= (df['title'].str.contains(search_query, case=False) | df['category'].str.contains(search_query, case=False))
    if sel_cat != "全部顯示": mask &= (df['category'] == sel_cat)
    if type_filter != "全部":
        mask &= (df['type'].str.contains(type_filter, case=False) | df['title'].str.contains(type_filter, case=False))

    results = df[mask]
    st.caption(f"🎯 找到 {len(results)} 筆結果 (一次最多顯示 20 筆以保穩定)")

    # 列表渲染 (使用 head(20) 避免手機一次載入太多 DOM 導致閃退)
    for _, row in results.head(20).iterrows():
        uid = row['uid']
        is_video = any(x in str(row['type']) for x in ["新鮮視", "側帶"])
        
        with st.expander(f"📄 {row['title']}"):
            t_low = str(row['title']).lower()
            if any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']):
                if st.button("▶️ 播放音訊", key=f"p_{uid}"):
                    with st.spinner("音檔轉碼中..."):
                        b64 = get_audio_base64(row['link'])
                        if b64: st.audio(b64)
                        else: st.error("音檔載入超時，請重試。")
            elif is_video:
                st.info("📺 影片權限：限同仁點擊下方按鈕觀看。")
            else:
                components.iframe(get_embed_url(row['link']), height=400)

            c1, c2 = st.columns(2)
            with c1: st.link_button("↗ 開啟檔案", row['link'], use_container_width=True)
            with c2:
                if st.button("🔗 分享/權限", key=f"s_{uid}", use_container_width=True):
                    show_share_dialog(row['title'], row['link'], uid, is_video=is_video)

if __name__ == "__main__":
    main()
