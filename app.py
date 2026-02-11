import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64
import hashlib
import time

# === 1. 設定區 ===
# 這裡維持妳原本的 CSV 連結
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?output=csv"
PASSWORD = "888"

# 重要：請將下方的網址替換為妳部署後實際的 Streamlit 網址
SITE_URL = "https://swd-case.streamlit.app" 

# === 2. 核心技術函數 ===

def generate_id(link):
    """利用連結產生唯一 ID，不受 CSV 順序影響"""
    return hashlib.md5(str(link).encode()).hexdigest()[:10]

@st.cache_data(ttl=300)
def get_audio_base64(url):
    """處理音訊 Base64，解決手機播放問題"""
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
    """轉換 Google Drive 連結為預覽格式"""
    if "drive.google.com" in link and "/view" in link:
        return link.replace("/view", "/preview")
    return link

# === 3. 資料載入與過濾 (排除案例資料庫) ===
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
        
        # 排除圖片與特定資料夾連結
        img_ext = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        df = df[~df['title'].astype(str).str.lower().str.endswith(img_ext)]
        df = df[~df['link'].astype(str).str.contains('/folders/')]
        
        # 預先計算每一行的 UID
        df['uid'] = df['link'].apply(generate_id)
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"表格載入失敗: {e}")
        return pd.DataFrame()

# === 4. 複製功能 UI ===
def render_copy_ui(label, text_to_copy):
    html_code = f"""
    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #eee; margin-bottom:10px;">
        <label style="font-size:12px; color:#666;">{label}</label>
        <input type="text" value="{text_to_copy}" id="copyInput" readonly style="width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px;">
        <button onclick="copyToClipboard()" style="width: 100%; padding: 8px; background: #0097DA; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">📋 點此複製網址</button>
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

    # 版權保護 CSS (隱藏下載鈕)
    st.markdown("""
        <style>
            audio::-webkit-media-controls-enclosure { overflow: hidden; }
            audio::-webkit-media-controls-panel { width: calc(100% + 30px); }
            .category-tag { background-color: #f1f3f4; color: #5f6368; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px; }
        </style>
    """, unsafe_allow_html=True)

    df = load_data()
    if df.empty: return

    # 檢查網址參數 (客戶預覽模式)
    params = st.query_params
    target_uid = params.get("id", None)

    # ------------------
    # A. 客戶預覽模式 (不需登入)
    # ------------------
    if target_uid:
        target_row = df[df['uid'] == target_uid]
        if not target_row.empty:
            item = target_row.iloc[0]
            st.subheader(f"🎵 作品預覽：{item['title']}")
            st.info("💡 此頁面為客戶試聽專用，已啟用版權保護。")
            
            with st.spinner("載入中..."):
                t_low = str(item['title']).lower()
                tp_low = str(item['type']).lower()
                
                # 音訊播放
                if any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in tp_low:
                    b64 = get_audio_base64(item['link'])
                    if b64:
                        st.markdown(f'<audio controls controlsList="nodownload" style="width:100%;"><source src="{b64}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
                # 影片/其他 則跳轉開啟 (最穩定)
                else:
                    st.success("✅ 檔案已就緒，請點擊下方按鈕開啟觀看。")
                    st.link_button("🎬 開啟影片預覽", item['link'], use_container_width=True)
            
            st.divider()
            if st.button("🏠 回到首頁"):
                st.query_params.clear()
                st.rerun()
            return

    # ------------------
    # B. 內部資料庫模式 (需要登入)
    # ------------------
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align: center;'>🔒 全家通路媒體資料庫</h2>", unsafe_allow_html=True)
        with st.form("login"):
            pw = st.text_input("輸入密碼解鎖", type="password")
            if st.form_submit_button("解鎖資料庫", use_container_width=True):
                if pw == PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("⚠️ 密碼錯誤")
        return

    # 搜尋介面
    search_query = st.text_input("🔍 搜尋品牌、產品關鍵字")
    c1, c2 = st.columns(2)
    with c1:
        cat_list = sorted([str(x) for x in df['category'].unique() if str(x).strip()])
        sel_cat = st.selectbox("📁 選擇分類", ["全部顯示"] + cat_list)
    with c2:
        type_filter = st.radio("📑 媒體類型", ["全部", "企頻", "新鮮視", "側帶"], horizontal=True)

    # 過濾邏輯
    mask = pd.Series([True] * len(df), index=df.index)
    if search_query:
        keys = search_query.lower().split()
        search_target = df['title'].astype(str) + " " + df['category'].astype(str) + " " + df['type'].astype(str)
        mask &= search_target.str.lower().apply(lambda x: any(k in x for k in keys))
    if sel_cat != "全部顯示":
        mask &= (df['category'].astype(str) == sel_cat)
    if type_filter != "全部":
        mask &= (df['type'].astype(str).str.contains(type_filter, case=False) | df['title'].astype(str).str.contains(type_filter, case=False))

    results = df[mask]
    st.caption(f"🎯 找到 {len(results)} 筆結果 (已自動排除案例資料庫)")

    # 渲染列表
    for _, row in results.iterrows():
        uid = row['uid']
        with st.expander(f"📄 {row['title']}"):
            st.markdown(f"<span class='category-tag'>{row['category']}</span><span class='category-tag'>{row['type']}</span>", unsafe_allow_html=True)
            
            t_low = str(row['title']).lower()
            tp_low = str(row['type']).lower()
            
            # --- 核心顯示邏輯：區分音訊與影片 ---
            # 1. 音訊檔：提供即時播放
            if any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in tp_low:
                if st.button("▶️ 載入音訊", key=f"play_{uid}"):
                    b64 = get_audio_base64(row['link'])
                    if b64: st.audio(b64)
                    else: st.error("載入失敗")
            
            # 2. 影片檔 (新鮮視、側帶)：建議跳轉開啟以防手機當機
            elif any(ext in t_low for ext in ['.mp4', '.mov']) or "新鮮視" in tp_low or "側帶" in tp_low:
                st.info("📺 影片檔案較大，建議點擊下方按鈕開啟預覽。")
                st.link_button("🎬 開啟影片預覽 (新分頁)", row['link'], use_container_width=True)
            
            # 3. 其他格式：使用 iframe
            else:
                st.components.v1.iframe(get_embed_url(row['link']), height=400)

            # 分享與開啟按鈕
            bt1, bt2 = st.columns(2)
            with bt1:
                st.link_button("↗ 直接開啟 (SharePoint)", row['link'], use_container_width=True)
            with bt2:
                if st.button("🔗 分享檔案 (內/外)", key=f"share_{uid}", use_container_width=True):
                    show_share_dialog(row['title'], row['link'], uid)

if __name__ == "__main__":
    main()
