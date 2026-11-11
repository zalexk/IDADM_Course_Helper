# IDADM Course Helper 使用指南 📘

歡迎使用 **IDADM Course Helper**！本指南將幫助你快速上手，高效規劃你的大學學業。

---
> [!IMPORTANT]
> 打開網頁如果遇到 `This app has gone to sleep due to inactivity. Would you like to wake it back up?`，請點擊 `Yes, get this app back up!` 按鈕。
>
> ![Screenshot of Sleep Page](assets/sleep_page.jpg)
>
> 這是因為資源所限，所使用的免費網頁托管平台設有自動休眠機制，當網頁未被訪問超過一段時間後，會自動休眠。

## 1. 登入與初始設定

### 登入帳戶
應用需要**註冊 / 登入帳戶**才能保存你的課程規劃。登入介面位於**左側邊欄 (Sidebar)**：

- **首次使用**：點擊 `Sign Up` 註冊帳戶（密碼需至少 8 位，並包含大小寫字母和數字）。
- **已有帳戶**：在側欄輸入用戶名和密碼，點擊 `Login` 登入。

> [!IMPORTANT]
>
> **訪客模式（未登入）下的選課操作不會被保存**，登入後這些修改會被清空。
>
> 未登入時也**無法使用 Planner 功能**。
>
> 首次以訪客身份編輯課程表時，應用會彈出 "Unsaved Edits" 提醒，確認後即可繼續。

登入後，你的每一次修改都會**自動同步保存**到雲端數據庫。下次打開網頁或刷新後，登入同一帳戶即可恢復你的課程規劃。

### 選擇第二主修
打開應用後，你首先需要選擇你的 **第二主修 (2nd Major)**。

- 在頁面頂部的下拉選單中選擇你的專業 (Major)。
- 系統會根據你的選擇，自動載入該專業的必修課 (Required Courses) 和選修課 (Electives) 要求。

> [!TIP]
>
> 必須先選擇第二主修 (2nd Major)，後續的課程規劃選項卡才會顯示。

> [!TIP]
>
> 想了解本工具最近的更新？主介面右下角的 **"Read what's new `v1.1`"** 摺疊區會列出各版本新功能（v1.1：支援課程導入、新增中英文語文課程；v1.0：支援登入儲存）。

## 2. 課程規劃流程

應用界面分為四個主要標籤頁 (Tab)，建議按以下順序進行規劃：

### 第一步：規劃大學必修課 (University Core)
在 **"University Core"** 標籤頁 (Tab) 中：

- **大學必修課目錄表**：系統已列出大學必修課程（如大學通識基礎課 UGFN1000 / UGFH1000、認識中國 UGCP1001、香港特區的憲制秩序 UGCP1002、數碼素養及計算思維 ENGG1003 等），你只需為每門課設定修讀學期。
- **手動輸入區**：**體育 (Physical Education)**、**書院通識 (College GE)** 和**四範圍通識 (Four Area of GE)** 因課程繁多、難以列舉，需要自行填寫課程編號、學分 (Credits) 和修讀學期（學期可先留空，勾選 Selected 後再到 Planner 排）；四範圍通識區另設 **UGEA1555 (Understanding Modern China)** 的目錄列（它與 UGCP1001 / UGCP1003 的二選一計法由 Planner 自動判斷）；**其他課程 (Other Courses)** 則用於填寫不在修讀方案 (study scheme) 內、但計劃修讀的課程——這些課程會計入學期學分負荷與總學分，但不會計入任何畢業要求項。
- **中文 (Chinese Language) 目錄表**：系統已列出中文課程（如 CHLT1001 / CHLT1002 / CHLT1303 / CHLT1308），你可增刪課程並為每門課設定修讀學期。
- **英文 (English Language) 目錄表**：系統會根據你選擇的**第二主修所屬學院**（工學院 Faculty of Engineering / 商學院 Faculty of Business Administration / 理學院 Faculty of Science），列出該學院合資格的英文課程（ELTU* 或對應的 ENG* 碼），你只需勾選並/或設定修讀學期。
- **Selected（已選）勾選列**：每張課程表的 **Credits 與 Study Period 之間**新增勾選框。勾選代表「計劃修讀」，**不必即刻決定學期**；未填 Study Period 的已選課程會集中在 Planner 的 **Selected Courses** 子標籤頁，之後再排學期。反過來，填了 Study Period 會**自動勾選**；清空 Study Period 只會把課程放回待排清單，不會刪除已勾選的課程。若取消勾選，系統會同時清空該課的 Study Period（目錄課程會從計劃中移除；自行輸入的課程會保留為草稿）。
- 在 **"Study Period"** 列中，為每門課選擇你打算修讀的學期 (Semester)（例如：`Year 1 Sem 1`）。若只想先記下課程、稍後再排，可留空並保持 Selected 勾選。

> [!Note]
>
> 由於我們可以在暑期學期同時在 CUHK 和 CUHK(SZ) 修讀課程，因此在選擇學期時，請注意校區分別。
>
> 暑期學期分為 `Year X Summer (CUHK)` 和 `Year X Summer (CUHKSZ)` 兩個選項。

> [!IMPORTANT]
>
> 添加課程時請注意所填寫的 **CUHK / CUHKSZ 校區欄位**，確保與修讀的校區相符。

### 第二步：規劃第一主修 (IDA)
在 **"Interdisciplinary Data Analytics"** 標籤頁 (Tab) 中：
- 規劃你的 **Faculty Package**、**Required Courses** 和 **COOP** 課程。
- **選修課規劃**：從 Group A 和 Group B 中選擇課程。
  - 要求：Group A 6 - 15 學分 + Group B 12 - 21 學分
  - 至少 12 學分為 3000 級或以上課程（其中包含 6 學分 4000 級課程）
- 系統會自動計算你是否滿足以上要求。

> [!IMPORTANT]
>
> 為方便計算畢業要求進度，請優先在 Faculty Package 和 Required Courses 選擇課程。
> 
> 因為計算畢業要求進度是根據 **你所選擇的課程所屬區域的類別計算** 。
> 
> > 假如你第一主修 (1st Major) 有一門課，且你的第二主修 (2nd Major) 也有這門課。
> >
> > 你在第一主修 (1st Major) 中的 Elective Course 中選擇修讀該課，將不會被系統識別為符合第二主修 (2nd Major) 的 Required Courses。

### 第三步：規劃第二主修
在以你選擇的 **專業 (Major) 名稱命名的標籤頁 (Tab)** 中：
- 重覆第二步規劃該專業的必修課 (Required Courses)、研究項目 (Research Component) 和選修課 (Electives)。

> [!NOTE]
>
> 第二主修中只有研究項目 (Research Component) 的成績會計入第二主修的 Major GPA。

---

## 3. 進度檢查與監控

所有課程規劃完成後，點擊 **"Planner"** 標籤頁 (Tab) 進行詳細檢查。

> [!IMPORTANT]
>
> **Planner 功能需要登入後才能使用**，未登入時該標籤頁只會提示你先登入。

### 批量導入已修課程 (Import Courses)
在 **"Planner"** 標籤頁 (Tab) 頂部，點擊 **"📥 Import Courses (導入已讀課程)"** 展開區：

- **上傳檔案**：建議上傳 CUSIS 中 *Academic Records* 的截圖（PNG / JPG / JPEG / WEBP）或 PDF。
- **預覽與編輯**：確認前請檢查預覽表格：
  - **Course ID**：可編輯，修正任何誤辨識的課程代碼。
  - **Recognized**：✓ 表示代碼已對應課程目錄；未對應（⚠）的課程僅在類別為大學必修輸入區（PE / College GE / Four Areas / English）時才會匯入，否則會被略過、需手動補錄。
  - **Existing Period**：你計劃中已儲存的學期（唯讀）；確認後將以 **Study Period** 覆寫（目錄課程若留空 Study Period 會被略過，既有計劃不會被刪除）。
  - **Study Period**：確認後將儲存的學期。
  - **Credits**：來自成績單的學分，僅對大學必修輸入區（PE / College GE / Four Areas）生效；其他類別一律使用課程目錄學分。
  - **Category**：該課程歸屬的要求類別，若系統建議錯誤可用下拉選單調整。
- **確認匯入**：點擊 `Confirm import 確認匯入`，課程將寫入對應的雲端資料表、標記為 **Selected**，並顯示匯入數量。

> [!IMPORTANT]
>
> 課程導入功能需要應用配置 LLM API Key（`.streamlit/secrets.toml` 中的 `LLM_API_KEY`，可選 `LLM_BASE_URL` 與 `COURSE_IMPORT_MODEL`），否則會提示金鑰缺失。匯入僅適用於已登入帳戶，訪客模式不會儲存。

### 已選課程 (Selected Courses)
**"Selected Courses"** 是 Planner 的第一個子標籤頁，集中列出所有**已勾選 Selected** 的課程（未排 Study Period 的課程會排在前面）：

- 在表格的 **Study Period** 欄為課程選擇學期，確認後課程會自動移到對應的 Year 子標籤頁。
- 表格預設把**未排學期的課程排在前面**，其餘按日曆順序（Year 1 Sem 1 起）排列。
- 可用 **Only show courses without a Study Period** 開關只看未排學期的課程（上方指標仍顯示整體數字）。
- 上方指標顯示：已選課程總數、未排學期課程數、未排學期學分。
- 未排學期的已選課程**計入畢業要求與總學分**，但**不計入學期學分上限**（因為還沒有所屬學期）。
- 在這裡清空 Study Period 會把課程放回本頁待排清單；課程不會被刪除。

### 學期視圖 (Year 1 - Year 4)
- **實時學分 (Credits) 計算**：查看每個學期 (Semester) 已排課程的總學分；未排學期的已選課程不在此顯示。
- 每個學年分為 **Sem 1 / Sem 2** 兩個子視圖，並顯示對應的修讀校區（例如 `Sem 1 (CUHK)`）。
- **暑假學期 (Summer Session)**：合併顯示 CUHK 和 CUHK(SZ) 兩校區暑課的學分。
- **學分 (Credits) 限制提醒**：
  - **常規學期**：9 - 18 學分 (Credits)（一年級學分上限為 19）。
  - **暑假學期 (Summer Term)**：上限 6 學分 (Credits)。
  - **全學年**：18 - 39 學分 (Credits)。
  - 如果超出或低於限制，系統會彈出**紅色提醒**，提醒你需要提交超修/減修申請。

### 畢業要求檢查 (Graduation Requirements)
在 **"Graduation Requirements"** 子標籤頁 (Sub-Tab) 中，你可以直觀地看到：
- 各個課程類別（University Core, 1st Major, 2nd Major）的學分 (Credits) 達成情況。
- 每個要求項目的 **Requirement / Credits / Fulfil** 狀態（University Core 的 `Credits` 為已修/已排學分，不封頂；Foundation 的 2 學分版本缺口會反映在 Four Areas 的 Requirement 上），哪些要求已符合，哪些仍未足夠。
- 頁面底部的 **Total Credit** 顯示總學分達成情況（目標 129 學分），包含已選但未排學期的課程。
- **GE 修訂自動換算**：系統已按 GE 修訂計算——`UGEA1555` (Understanding Modern China) 在未修 `UGCP1001`/`UGCP1003` 時折算為 `UGCP1001`（1 學分）+ 2 學分四範圍通識，否則按 3 學分四範圍通識計；若修讀 2 學分的 `UGFH1002`/`UGFN1002`，Foundation 不足的學分會自動要求以四範圍通識補足（Four Areas 的 Requirement 會相應提高並顯示提示）。

> [!IMPORTANT]
>
> **中文 (Chinese Language) 與英文 (English Language) 語文要求現已可由系統根據課程清單學分自動核算**，GE 修訂下的 `UGEA1555` 與 Foundation 過渡換算亦已自動處理。其餘大學必修 (University Core) 類別（如 PE / College GE / 四範圍通識的具體選課）仍請自行對照官方要求判斷。

> [!IMPORTANT]
>
> 畢業要求檢查僅基於目前選課情況，不代表實際畢業要求。

### 總覽與導出 (Overall)
在 **"Overall"** 子標籤頁 (Sub-Tab) 中：

- **預覽總表**：查看所有課程的排期表（課程會按修讀學期的校區顯示對應的課程編號）。已選但未排學期的課程會以空白 Study Period 列出。
- **導出文件**：
  - 點擊 **"Export as PDF"**：導出為 PDF 文件；若有未排學期的已選課程，文件末尾會多一頁 **"Selected Courses (No Study Period)"** 及總學分。
  - 點擊 **"Export as Word"**：導出為 `.docx` 文件，同樣包含上述待排課程段落。

---

## 💡 注意事項
- **數據保存**：登入後，你的每一次修改都會**自動保存**到雲端數據庫，刷新頁面或關閉網頁後數據仍然保留，登入同一帳戶即可恢復。
- **訪客模式**：未登入時所做的修改**不會被保存**，且登入後會被清空。建議先登入再開始規劃。
> [!CAUTION]
>
> 目前暫不支持導入功能，數據與帳戶綁定。請妥善保管你的用戶名和密碼，以免無法取回課程規劃。

- **官方參考**：本工具僅供參考，請查閱 CUSIS / SIS 等官方系統和[課程官網](https://www.idadm.cdmp.cuhk.edu.hk/)。

---
*祝你在 IDADM 的學習旅程一帆風順！*

> [!NOTE]
>
> 本文使用 AI 自動撰寫，經人工修改。
