import streamlit as st
import pandas as pd

# 模擬從 Google Sheet 讀取進來的兩張資料表
# 實際執行時請替換成您原本讀取 Sheet 的 st.connection 或 pd.read_csv 邏輯
@st.cache_data
def load_data():
    # 這裡只是示意，請維持您原本讀取「總資料庫」與「clients」的方式
    # df_cases = ... (讀取總資料庫)
    # df_logos = ... (讀取clients分頁)
    return df_cases, df_logos

df_cases, df_logos = load_data()

st.title("🎵 聲活案例與 Logo 智能篩選系統")

# ================= 第一階段：案例搜尋與勾選 =================
st.subheader("第一步：搜尋並勾選案例（至多 6 個）")

# 這裡可以加上您原本的關鍵字搜尋或下拉選單篩選器
search_query = st.text_input("輸入關鍵字搜尋案例（如：建案、飮品）：")
filtered_cases = df_cases[df_cases['Title'].str.contains(search_query, case=False, na=False)] if search_query else df_cases

# 用來記錄使用者勾選了哪些案例的 Index
selected_case_indices = []

# 建立表格並在每列前方加上 Checkbox
for index, row in filtered_cases.iterrows():
    # 用 Columns 讓 Checkbox 和資料排在同一行
    col1, col2, col3, col4 = st.columns([0.5, 2, 4, 4])
    with col1:
        is_checked = st.checkbox("", key=f"case_{index}")
        if is_checked:
            selected_case_indices.append(index)
    with col2:
        st.write(row['Category'])
    with col3:
        st.write(row['Short'])
    with col4:
        st.markdown(f"[音檔連結]({row['Link']})")

st.markdown(f"📊 目前已勾選 **{len(selected_case_indices)} / 6** 個案例")

# ================= 條件檢查與按鈕 =================
if len(selected_case_indices) > 6:
    st.error("⚠️ 您的勾選超過 6 個囉！請取消部分勾選再繼續。")
    st.stop() # 停止往下執行

# 當使用者勾選完，按下 OK 按鈕
if st.button("OK！產生 Logo 建議", type="primary"):
    if len(selected_case_indices) == 0:
        st.warning("請至少勾選一個案例。")
    else:
        # 將已勾選的案例記錄到 session_state，避免網頁重整時消失
        st.session_state['selected_cases'] = df_cases.loc[selected_case_indices]
        st.session_state['show_logos'] = True

# ================= 第二階段：Logo 智慧建議與第二次勾選 =================
if st.session_state.get('show_logos', False):
    st.write("---")
    st.subheader("第二步：根據所選案例類別，推薦相關 Logo")
    
    # 1. 提取所選案例的「所有類別」（自動去重）
    chosen_categories = st.session_state['selected_cases']['Category'].unique()
    st.info(f"💡 系統偵測到您選擇的案例包含以下類別：{', '.join(chosen_categories)}。已為您自動匹配相對應的 Logo！")
    
    # 2. 從 df_logos 中篩選出符合這些類別的 Logo 檔
    recommended_logos = df_logos[df_logos['category'].isin(chosen_categories)]
    
    if recommended_logos.empty:
        st.warning("目前的 Logo 資料夾中，暫時沒有符合這些類別的 Logo 檔案。")
    else:
        # 3. 讓使用者做第二次勾選
        selected_logo_links = []
        
        # 網頁排版：用網格(Grid)方式呈現 Logo 推薦
        logo_cols = st.columns(3) # 每行顯示 3 個 Logo
        
        for i, (idx, logo_row) in enumerate(recommended_logos.iterrows()):
            with logo_cols[i % 3]:
                # 顯示 Logo 名稱與勾選方塊
                logo_checked = st.checkbox(f"{logo_row['Clients客戶名稱/品名']}", key=f"logo_{idx}")
                # 這裡可以用 st.image 秀出圖片（如果您的連結可以直接外連圖檔的話）
                # st.image(logo_row['Logo_link'], width=100)
                
                if logo_checked:
                    selected_logo_links.append(logo_row['Logo_link'])
        
        # 4. 最終輸出
        if st.button("確認最終選擇"):
            st.success(f"🎉 提案配置完成！您共選擇了 {len(selected_logo_links)} 個 Logo。")
            # 這裡看您是要匯出成 PDF、產出新表格、還是傳送給誰，就可以接著寫
