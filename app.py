import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64
import hashlib
import os
import tempfile

# === 1. 設定區 ===
# ⚠️ 請確保這兩個網址分別是「總資料庫」分頁與「Clients」分頁獨立發布為 CSV 的網址
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?gid=0&single=true&output=csv"
CSV_LOGO_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?gid=1588470763&single=true&output=csv" # 👈 請務必填入 Clients 分頁專屬的 CSV 網址

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
    try:
        logo_df = pd.read_csv(CSV_LOGO_URL, on_bad_lines='skip', engine='python')
        logo_df.columns = [str(c).strip().lower() for c in logo_df.columns]
        
        rename_dict = {}
        for c in logo_df.columns:
            if 'client' in c or '客戶' in c or '品名' in c or 'brand' in c:
                rename_dict[c] = 'client_name'
            if 'link' in c or '網址' in c or 'logo' in c:
                rename_dict[c] = 'logo_link'
            if 'category' in c or '分類' in c:
                rename_dict[c] = 'category'
                
        logo_df = logo_df.rename(columns=rename_dict)
        if 'client_name' not in logo_df.columns and len(logo_df.columns) > 1:
            logo_df.columns.values[1] = 'client_name'
            
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
    if 'selected_uids' not in st.session_state:
        st.session_state.selected_uids = []
    if 'confirmed_stage' not in st.session_state:
        st.session_state.confirmed_stage = False

    df = load_data()
    logo_df = load_logo_data()
    
    if df.empty:
        st.error("目前無法連線至總資料庫，請檢查發布設定。")
        return

    params = st.query_params
    target_uid = params.get("id", None)

    if target_uid:
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

    # -----------------------------------------------------------------
    # 【第一階段】常駐戰情管理台 + 搜尋列表 (支援手機優化被動聽感)
    # -----------------------------------------------------------------
    if not st.session_state.confirmed_stage:
        st.markdown("<h2 style='text-align: center;'>📂 全家通路媒體資料庫</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        # 💡 圖2功能實現：常駐戰情管理台 (釘選在頂部)
        if st.session_state.selected_uids:
            st.markdown("### 📊 戰情管理台 (已挑選項目)")
            
            for idx, uid in enumerate(st.session_state.selected_uids):
                matched_rows = df[df['uid'] == uid]
                if matched_rows.empty: continue
                case_info = matched_rows.iloc[0]
                
                # 橫向輕量化排版
                col_name, col_audio, col_del = st.columns([5, 4, 1])
                with col_name:
                    st.caption(f"**案例 {idx+1}**")
                    st.markdown(f"📄 {case_info['short']}")
                with col_audio:
                    # 💡 圖2修正核心：改回「載入音訊」原始被動按鈕，防止手機網頁載入過重卡死
                    if st.button("▶️ 載入音訊", key=f"panel_play_{uid}", use_container_width=True):
                        with st.spinner("載入中..."):
                            b64 = get_audio_base64(case_info['link'])
                            if b64:
                                st.audio(b64)
                            else:
                                st.error("音檔讀取失敗")
                with col_del:
                    st.markdown("剔除")
                    if st.button("❌", key=f"panel_del_{uid}", use_container_width=True):
                        st.session_state.selected_uids.remove(uid)
                        st.rerun()
            st.markdown("---")

        # 進度與按鈕合併顯示列
        c_status, c_ok = st.columns([3, 2])
        with c_status:
            st.markdown(f"📥 已挑選： **{len(st.session_state.selected_uids)} / 6**")
        with c_ok:
            # 💡 圖1修正核心：將按鈕字樣改名為「確認挑選項目」
            if st.button("👌 確認挑選項目", use_container_width=True, type="primary" if st.session_state.selected_uids else "secondary"):
                if st.session_state.selected_uids:
                    st.session_state.confirmed_stage = True
                    st.rerun()
                else:
                    st.warning("請先在下方案例旁勾選！")

        st.markdown("---")
        
        # 關鍵字搜尋與過濾
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
        
        st.markdown("#### 📂 搜尋結果案例列表 (請在下方挑選打勾)")
        current_results = results.head(st.session_state.display_count)
        
        for _, row in current_results.iterrows():
            uid = row['uid']
            display_name = row['short']
            t_low, tp_low = str(row['title']).lower(), str(row['type']).lower()
            
            is_audio = any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in tp_low
            is_video = any(x in tp_low for x in ["新鮮視", "側帶", "demo"]) or any(ext in t_low for ext in ['.mp4', '.mov'])
            is_image = any(ext in t_low for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])

            col_check, col_exp = st.columns([1, 9])
            with col_check:
                is_checked_before = uid in st.session_state.selected_uids
                check_clicked = st.checkbox("選取", key=f"chk_{uid}", value=is_checked_before, label_visibility="collapsed")
                if check_clicked and uid not in st.session_state.selected_uids:
                    if len(st.session_state.selected_uids) < 6:
                        st.session_state.selected_uids.append(uid)
                        st.rerun()
                    else: st.error("❌ 最多只能打包 6 個案例！")
                elif not check_clicked and uid in st.session_state.selected_uids:
                    st.session_state.selected_uids.remove(uid)
                    st.rerun()

            with col_exp:
                with st.expander(f"📄 {display_name}"):
                    if is_audio:
                        if st.button("▶️ 載入音訊", key=f"p_{uid}"):
                            b64 = get_audio_base64(row['link'])
                            if b64: st.audio(b64)
                    elif is_video: st.info("📺 影片預覽：限同仁點擊下方『開啟檔案』觀看。")
                    elif is_image: st.warning("🖼️ 此為『圖片檔』。同仁請點擊下方『開啟檔案』查看。")
                    else: components.iframe(get_embed_url(row['link']), height=400)
                    
                    bt1, bt2 = st.columns(2)
                    with bt1: st.link_button("↗ 開啟檔案", row['link'], use_container_width=True)
                    with bt2:
                        if st.button("🔗 分享檔案", key=f"s_{uid}", use_container_width=True):
                            show_share_dialog(display_name, row['link'], uid, is_video=is_video, is_image=is_image)

        if total_results > st.session_state.display_count:
            if st.button(f"🔽 展開更多案例", use_container_width=True):
                st.session_state.display_count += 20
                st.rerun()

    # -----------------------------------------------------------------
    # 【第二階段】配置與最終 PPTX 封裝生成頁面
    # -----------------------------------------------------------------
    if st.session_state.confirmed_stage and st.session_state.selected_uids:
        st.markdown("""
        <div style="background-color:#e0f2fe; padding:20px; border-radius:10px; border-left:5px solid #0284c7; margin: 15px 0;">
            <h4 style="color:#0369a1; margin:0;">🎯 第二階段：確認各案例 Logo 與自訂簡報大標</h4>
            <p style="font-size:14px; color:#0c4a6e; margin:5px 0 0 0;">請確認下方各案例對應的 Logo，音檔將在下載時「實體嵌入」至簡報中。</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🖋️ 編輯 PPT 簡報大標題")
        custom_ppt_title = st.text_input("請輸入您想要的 PPT 簡報主標題：", value="合作夥伴案例分享", key="custom_ppt_title_input")
        st.markdown("---")
        
        logo_options = ["請選擇確切客戶 Logo"] + sorted(list(logo_df['client_name'].unique())) if not logo_df.empty else ["請選擇確切客戶 Logo"]
        final_pack_pairs = {}

        for idx, picked_uid in enumerate(st.session_state.selected_uids):
            matched_rows = df[df['uid'] == picked_uid]
            if matched_rows.empty: continue
            case_row = matched_rows.iloc[0]
            case_title = str(case_row['short'])
            
            guessed_logo_for_this_row = "請選擇確切客戶 Logo"
            if not logo_df.empty:
                for client in logo_df['client_name'].unique():
                    pure_name = str(client).split('_')[-1] if '_' in str(client) else str(client)
                    if pure_name in case_title or str(client) in case_title:
                        guessed_logo_for_this_row = client
                        break
            
            c_label, c_case_lbl, c_logo_sel, c_del = st.columns([1, 4, 3, 1])
            with c_label:
                st.markdown(f"\n\n**案例 {idx+1}**")
            with c_case_lbl:
                st.markdown("案例名稱")
                st.info(f"📄 {case_title}")
            with c_logo_sel:
                st.markdown("對應 Logo")
                default_idx = logo_options.index(guessed_logo_for_this_row) if guessed_logo_for_this_row in logo_options else 0
                chosen_logo_for_row = st.selectbox(f"選Logo_{picked_uid}", options=logo_options, index=default_idx, key=f"sel_logo_pair_{picked_uid}", label_visibility="collapsed")
                
                logo_row = logo_df[logo_df['client_name'] == chosen_logo_for_row]
                raw_url = logo_row.iloc[0]['logo_link'] if not logo_row.empty else ""
                file_id = ""
                if "/file/d/" in raw_url: file_id = raw_url.split("/file/d/")[1].split("/")[0]
                elif "id=" in raw_url: file_id = raw_url.split("id=")[1].split("&")[0]
                
                final_pack_pairs[picked_uid] = {
                    'case_title': case_title,
                    'case_audio_link': case_row['link'], 
                    'logo_name': chosen_logo_for_row,
                    'logo_file_id': file_id
                }
            with c_del:
                st.markdown("剔除")
                if st.button("❌", key=f"del_item_{picked_uid}", use_container_width=True):
                    st.session_state.selected_uids.remove(picked_uid)
                    st.rerun()

            st.markdown("<div style='margin-bottom:-10px;'></div>", unsafe_allow_html=True) 

        st.markdown("---")
        
        c_back, c_action = st.columns([1, 4])
        with c_back:
            # 💡 點擊「返回挑選項目」按鈕時保留當前剩餘進度
            if st.button("🔙 返回挑選更多案例", use_container_width=True, key="unique_back_btn"):
                st.session_state.confirmed_stage = False
                st.rerun()
                
        with c_action:
            if final_pack_pairs:
                import io
                from datetime import datetime
                from pptx import Presentation
                from pptx.util import Inches, Pt
                
                ppt_buffer = io.BytesIO()
                
                if st.button("🎨 確認無誤！開始排版並下載六宮格提案 PPTX", use_container_width=True, type="primary"):
                    with st.spinner("🚀 正在下載音檔與 Logo，並自動排版六宮格簡報中..."):
                        try:
                            prs = Presentation()
                            prs.slide_width = Inches(13.333)
                            prs.slide_height = Inches(7.5)
                            slide = prs.slides.add_slide(prs.slide_layouts[6])
                            
                            title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12), Inches(0.8))
                            title_box.text_frame.paragraphs[0].text = str(custom_ppt_title).strip()
                            title_box.text_frame.paragraphs[0].font.size = Pt(28)
                            title_box.text_frame.paragraphs[0].font.bold = True
                            title_box.text_frame.paragraphs[0].font.name = "Microsoft JhengHei"
                            
                            x_coords = [Inches(0.6), Inches(4.8), Inches(9.0)]
                            y_coords = [Inches(1.8), Inches(4.6)]
                            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                            
                            for idx, (uid, info) in enumerate(final_pack_pairs.items()):
                                if idx >= 6: break 
                                row_idx, col_idx = idx // 3, idx % 3   
                                current_x, current_y = x_coords[col_idx], y_coords[row_idx]
                                
                                text_box = slide.shapes.add_textbox(current_x, current_y, Inches(3.8), Inches(0.5))
                                text_box.text_frame.word_wrap = True
                                p_case = text_box.text_frame.paragraphs[0]
                                p_case.text = f"🔹 {info['case_title']}"
                                p_case.font.size = Pt(11)
                                p_case.font.name = "Microsoft JhengHei"
                                
                                if info['case_audio_link']:
                                    try:
                                        audio_url = info['case_audio_link'].split('?')[0] + "?download=1" if "sharepoint.com" in info['case_audio_link'] else info['case_audio_link']
                                        resp_audio = requests.get(audio_url, headers=headers, timeout=15)
                                        if resp_audio.status_code == 200:
                                            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_audio:
                                                tmp_audio.write(resp_audio.content)
                                                tmp_audio_path = tmp_audio.name
                                            
                                            slide.shapes.add_movie(
                                                tmp_audio_path,
                                                current_x + Inches(0.2),
                                                current_y + Inches(0.75),
                                                width=Inches(0.4),
                                                height=Inches(0.4),
                                                poster_frame_image=None,
                                                mime_type='audio/mpeg'
                                            )
                                            try: os.unlink(tmp_audio_path)
                                            except: pass
                                    except: pass
                                
                                if info.get('logo_file_id') and info['logo_name'] != "請選擇確切客戶 Logo":
                                    try:
                                        direct_img_url = f"https://lh3.googleusercontent.com/u/0/d/{info['logo_file_id']}"
                                        resp_logo = requests.get(direct_img_url, headers=headers, timeout=10)
                                        if resp_logo.status_code == 200 and len(resp_logo.content) > 1000:
                                            slide.shapes.add_picture(
                                                io.BytesIO(resp_logo.content), 
                                                current_x + Inches(0.9), 
                                                current_y + Inches(0.65), 
                                                width=Inches(1.6)
                                            )
                                    except: pass
                                        
                            prs.save(ppt_buffer)
                            ppt_buffer.seek(0)
                            today_str = datetime.now().strftime("%Y%m%d")
                            
                            st.download_button(
                                label="💾 簡報封裝完畢！點此儲存 PPTX 檔案至電腦",
                                data=ppt_buffer,
                                file_name=f"媒體通路提案簡報_{today_str}.pptx",
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                use_container_width=True,
                                type="primary"
                            )
                        except Exception as e:
                            st.error(f"❌ 簡報自動生成失敗，原因：{str(e)}")
            else:
                st.warning("⚠️ 您的挑選清單目前為空，請點選左下角返回重新挑選案例。")
        st.markdown("---")

if __name__ == "__main__":
    main()
