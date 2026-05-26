import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64
import hashlib

# === 1. 設定區 ===
# ⚠️ 請確保這兩個網址分別是「總資料庫」分頁與「Clients」分頁獨立發布為 CSV 的網址
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?output=csv"
CSV_LOGO_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?gid=2040608076&single=true&output=csv" # 👈 請務必填入 Clients 分頁專屬的 CSV 網址

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

def get_image_download_url(link):
    """自動將 Google Drive 預覽網址轉為直連下載網址，解決破圖問題"""
    if not isinstance(link, str): return ""
    if "drive.google.com" in link and "/file/d/" in link:
        file_id = link.split("/file/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return link

# === 3. 資料載入與過濾核心 ===
@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(CSV_URL, on_bad_lines='skip', engine='python')
        df.columns = [str(c).strip().lower() for c in df.columns]
        for col in ['title', 'link', 'category', 'type', 'short']:
            if col not in df.columns: df[col] = ""
        df = df.fillna("")
        df['short'] = df.apply(lambda r: r['short'] if str(r['short']).strip() != "" else r['title'], axis=1)
        df = df[~df['category'].astype(str).str.contains("案例資料庫", na=False)]
        df = df[~df['link'].astype(str).str.contains('/folders/')]
        df['uid'] = df['link'].apply(generate_id)
        return df.reset_index(drop=True)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_logo_data():
    """精準對齊您 Clients 分頁的欄位結構"""
    try:
        logo_df = pd.read_csv(CSV_LOGO_URL, on_bad_lines='skip', engine='python')
        logo_df.columns = [str(c).strip().lower() for c in logo_df.columns]
        
        # 尋找並修正您的特殊欄位名稱
        rename_dict = {}
        for c in logo_df.columns:
            if 'client' in c or '客戶' in c or '品名' in c:
                rename_dict[c] = 'client_name'
            if 'link' in c or '網址' in c or 'logo' in c:
                rename_dict[c] = 'logo_link'
                
        logo_df = logo_df.rename(columns=rename_dict)
        return logo_df.fillna("")
    except:
        return pd.DataFrame(columns=['category', 'client_name', 'logo_link'])

# === 4. UI 元件 ===
def render_copy_ui(label, text_to_copy, is_disabled=False, warning_msg=""):
    if is_disabled:
        html_code = f"""
        <div style="background-color:#fff5f5;padding:12px;border-radius:8px;border:1px solid #feb2b2;margin-bottom:10px;">
            <label style="font-size:12px;color:#c53030;font-weight:bold;">{label}</label>
            <p style="font-size:13px;color:#333;margin:8px 0;line-height:1.4;">⚠️ {warning_msg}</p>
        </div>
        """
    else:
        html_code = f"""
        <div style="background-color:#f8f9fa;padding:10px;border-radius:8px;border:1px solid #eee;margin-bottom:10px;">
            <label style="font-size:12px;color:#666;">{label}</label>
            <input type="text" value="{text_to_copy}" id="copyInput" readonly style="width:100%;padding:8px;margin:5px 0;border:1px solid #ddd;border-radius:4px;">
            <button onclick="copyToClipboard()" style="width:100%;padding:10px;background:#0097DA;color:white;border:none;border-radius:5px;cursor:pointer;font-weight:bold;">📋 點此複製網址</button>
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

# === 5. 主程式架構 ===
def main():
    st.set_page_config(page_title="全家通路媒體資料庫", layout="centered")
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'display_count' not in st.session_state:
        st.session_state.display_count = 20

    df = load_data()
    logo_df = load_logo_data()
    
    if df.empty:
        st.error("目前無法連線至總資料庫，請檢查發布設定。")
        return

    params = st.query_params
    target_uid = params.get("id", None)

    if target_uid:
        # (保持原有的客戶單頁試聽模式不變...)
        target_row = df[df['uid'] == target_uid]
        if not target_row.empty:
            item = target_row.iloc[0]
            t_low, tp_low = str(item['title']).lower(), str(item['type']).lower()
            is_vid = any(x in tp_low for x in ["新鮮視", "側帶", "demo"]) or any(ext in t_low for ext in ['.mp4', '.mov'])
            is_img = any(ext in t_low for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
            if is_vid or is_img:
                st.error("此檔案涉及版權保護，不開放對外預覽。")
                return
            st.subheader(f"🎵 作品預覽：{item['short']}")
            b64 = get_audio_base64(item['link'])
            if b64: st.markdown(f'<audio controls controlsList="nodownload" style="width:100%;"><source src="{b64}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
            if st.button("🏠 回到首頁"): st.query_params.clear(); st.rerun()
            return

    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align: center;'>🔒 全家通路媒體資料庫</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            pw = st.text_input("請輸入內部資料庫密碼", type="password")
            if st.form_submit_button("解鎖系統", use_container_width=True):
                if pw == PASSWORD: st.session_state.logged_in = True; st.rerun()
                else: st.error("密碼錯誤")
        return

    # 搜尋與過濾元件
    search_query = st.text_input("🔍 關鍵字搜尋 (比對標題內容)")
    if 'last_search' not in st.session_state or st.session_state.last_search != search_query:
        st.session_state.display_count = 20
        st.session_state.last_search = search_query

    c1, c2 = st.columns(2)
    with c1:
        cat_list = sorted([str(x) for x in df['category'].unique() if str(x).strip()])
        sel_cat = st.selectbox("📂 總資料庫分類過濾", ["全部"] + cat_list)
    with c2:
        type_filter = st.radio("📑 類型過濾", ["全部", "企頻", "新鮮視", "側帶", "demo"], horizontal=True)

    mask = pd.Series([True] * len(df), index=df.index)
    if search_query:
        mask &= (df['title'].str.contains(search_query, case=False) | df['category'].str.contains(search_query, case=False))
    if sel_cat != "全部":
        mask &= (df['category'] == sel_cat)
    if type_filter != "全部":
        mask &= (df['type'].str.contains(type_filter, case=False) | df['title'].str.contains(type_filter, case=False))

    results = df[mask]
    total_results = len(results)
    
    # =====================================================================
    # 🆕 兩階段推進式：案例勾選 ➡️ 觸發 Logo 建議區
    # =====================================================================
    
    # 初始化記憶庫
    if 'selected_uids' not in st.session_state:
        st.session_state.selected_uids = []  # 存被勾選案例的 uid
    if 'confirmed_stage' not in st.session_state:
        st.session_state.confirmed_stage = False  # 是否按下 OK 進入第二階段

    # 頂部固定顯示目前已勾選的進度
    st.markdown("---")
    c_status, c_ok = st.columns([4, 1])
    with c_status:
        st.markdown(f"### 📥 已挑選案例進度： **{len(st.session_state.selected_uids)} / 6**")
        # 顯示目前勾了哪些
        if st.session_state.selected_uids:
            picked_shorts = df[df['uid'].isin(st.session_state.selected_uids)]['short'].tolist()
            st.caption(f"已選：{', '.join(picked_shorts)}")
    with c_ok:
        # 當有選東西時，OK 按鈕才會亮起
        if st.button("👌 確認選好", use_container_width=True, type="primary" if st.session_state.selected_uids else "secondary"):
            if st.session_state.selected_uids:
                st.session_state.confirmed_stage = True
                st.rerun()
            else:
                st.warning("請先在下方案例旁勾選！")

    # -----------------------------------------------------------------
    # 【階段二】跳出 Logo 建議與打包下載頁面
    # -----------------------------------------------------------------
    if st.session_state.confirmed_stage and st.session_state.selected_uids:
        st.markdown("""
        <div style="background-color:#e0f2fe; padding:20px; border-radius:10px; border-left:5px solid #0284c7; margin: 15px 0;">
            <h4 style="color:#0369a1; margin:0;">🎯 第二階段：確認品牌 Logo 與打包</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # 1. 智慧型 Logo 關鍵字猜測
        first_picked_uid = st.session_state.selected_uids[0]
        first_picked_title = str(df[df['uid'] == first_picked_uid].iloc[0]['short'])
        
        guessed_logo = "請選擇確切客戶 Logo"
        if not logo_df.empty:
            for client in logo_df['client_name'].unique():
                pure_name = str(client).split('_')[-1] if '_' in str(client) else str(client)
                if pure_name in first_case_title or str(client) in first_picked_title:
                    guessed_logo = client
                    break

        col_logo_1, col_logo_2 = st.columns(2)
        with col_logo_1:
            st.markdown("**💡 系統提供的 Logo 建議**")
            logo_options = ["請選擇確切客戶 Logo"] + sorted(list(logo_df['client_name'].unique())) if not logo_df.empty else ["請選擇確切客戶 Logo"]
            
            # 設定下拉選單預設值
            default_idx = logo_options.index(guessed_logo) if guessed_logo in logo_options else 0
            
            final_logo = st.selectbox("若建議不準，可手動修正：", options=logo_options, index=default_idx)
            
        with col_logo_2:
            st.markdown("**🚀 執行最終打包**")
            st.write("") # 留白對齊
            if final_logo != "請選擇確切客戶 Logo":
                if st.button("🔥 開始打包下載所有素材", use_container_width=True):
                    # 撈取對應 Logo 的網址
                    logo_row = logo_df[logo_df['client_name'] == final_logo]
                    raw_url = logo_row.iloc[0]['logo_link'] if not logo_row.empty else ""
                    dl_logo_url = get_image_download_url(raw_url)
                    
                    st.success(f"🎉 成功配對！即將下載「{final_logo}」的 Logo： {dl_logo_url}")
                    st.info(f"正在打包您勾選的 {len(st.session_state.selected_uids)} 個 OneDrive 案例檔案...")
            else:
                st.warning("請先指派一個正確的 Logo 品牌。")
                
        if st.button("🔙 返回重新挑選案例", use_container_width=True):
            st.session_state.confirmed_stage = False
            st.rerun()
            
        st.markdown("---")

    # -----------------------------------------------------------------
    # 【階段一】渲染列表與動態勾選區
    # -----------------------------------------------------------------
    st.markdown("#### 📂 搜尋結果案例列表 (請在下方挑選打勾)")
    
    current_results = results.head(st.session_state.display_count)
    for _, row in current_results.iterrows():
        uid = row['uid']
        display_name = row['short']
        t_low, tp_low = str(row['title']).lower(), str(row['type']).lower()
        
        is_audio = any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in tp_low
        is_video = any(x in tp_low for x in ["新鮮視", "側帶", "demo"]) or any(ext in t_low for ext in ['.mp4', '.mov'])
        is_image = any(ext in t_low for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])

        # 💡 核心改動：在每一個 Expand 展開前，並列一個 Checkbox 放左邊
        col_check, col_exp = st.columns([1, 9])
        
        with col_check:
            # 檢查這個案例先前有沒有被勾選過
            is_checked_before = uid in st.session_state.selected_uids
            
            # 建立勾選方塊
            check_clicked = st.checkbox("選取", key=f"chk_{uid}", value=is_checked_before, label_visibility="collapsed")
            
            # 狀態處理：當同仁點擊打勾或取消
            if check_clicked and uid not in st.session_state.selected_uids:
                if len(st.session_state.selected_uids) < 6:
                    st.session_state.selected_uids.append(uid)
                    st.rerun() # 立刻重整更新頂部的進度條
                else:
                    st.error("❌ 最多只能打包 6 個案例！")
            elif not check_clicked and uid in st.session_state.selected_uids:
                st.session_state.selected_uids.remove(uid)
                st.rerun()

        with col_exp:
            # 原本的 Expander 內容完全不動
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
                    if st.button("🔗 分享檔案", key=f"s_{uid}", use_container_width=True):
                        show_share_dialog(display_name, row['link'], uid, is_video=is_video, is_image=is_image)

    # 展開更多案例按鈕
    if total_results > st.session_state.display_count:
        if st.button(f"🔽 展開更多案例", use_container_width=True):
            st.session_state.display_count += 20
            st.rerun()

if __name__ == "__main__":
    main()
