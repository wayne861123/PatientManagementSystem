/**
 * 醫師門診管理系統 - JavaScript 函式庫
 * ===========================================================================
 * 包含所有頁面共用的 JavaScript 函式
 * ===========================================================================
 */

/* --------------------------------------------------------------------------
   1. 側邊欄功能
   -------------------------------------------------------------------------- */

/**
 * 切換側邊欄展開/收合狀態
 * 收合時顯示 emoji icon，展開時顯示完整文字
 */
function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    const home_page = document.getElementById("home-page");
    const doctor_management = document.getElementById("management-doctor");
    const disease_management = document.getElementById("management-disease");
    const examination_management = document.getElementById("management-examination");
    const medicine_management = document.getElementById("management-medicine");
    
    if (sidebar.classList.toggle("sidebar-collapse")) {
        home_page.textContent = "🏠";
        doctor_management.textContent = "👩‍⚕️";
        disease_management.textContent = "🦠";
        examination_management.textContent = "📝";
        medicine_management.textContent = "💊";
    }
    if (sidebar.classList.toggle("sidebar-expand")) {
        home_page.textContent = "首頁";
        doctor_management.textContent = "醫師管理";
        disease_management.textContent = "疾病管理";
        examination_management.textContent = "檢查項目管理";
        medicine_management.textContent = "藥物管理";
    }
    const isCollapsed = sidebar.classList.contains("sidebar-collapse");
    localStorage.setItem("sidebarCollapsed", isCollapsed);
}

/* --------------------------------------------------------------------------
   2. 縣市區域資料與更新
   -------------------------------------------------------------------------- */

/**
 * 台灣各縣市的鄉鎮市區資料
 * 用於地址選擇的連動下拉選單
 */
const districts = {
    '台北市': ['中正區', '大同區', '中山區', '松山區', '大安區', '萬華區', '信義區', '士林區', '北投區', '內湖區', '南港區', '文山區'],
    '新北市': ['板橋區', '三重區', '中和區', '永和區', '新莊區', '新店區', '土城區', '蘆洲區', '樹林區', '鶯歌區', '三峽區', '淡水區', '汐止區', '林口區', '八德區', '泰山區', '林園區', '五股區', '貢寮區', '雙溪區', '石門區', '坪林區', '石碇區', '深坑區', '平溪區', '瑞芳區', '烏來區'],
    '桃園市': ['桃園區', '中壢區', '平鎮區', '楊梅區', '龍潭區', '龜山區', '大溪區', '八德區', '大園區', '蘆竹區', '觀音區', '新屋區', '復興區', '楊梅區', '南區'],
    '台中市': ['中區', '東區', '南區', '西區', '北區', '西屯區', '南屯區', '北屯區', '豐原區', '大里區', '太平區', '清水區', '沙鹿區', '潭子區', '大雅區', '梧棲區', '后里區', '外埔區', '大甲區', '石岡區', '新社區', '和平區', '神岡區', '大肚區', '龍井區', '霧峰區', '烏日區'],
    '台南市': ['中西區', '東區', '南區', '北區', '安平區', '安南區', '永康區', '歸仁區', '新化區', '左鎮區', '玉井區', '楠西區', '南化區', '仁德區', '關廟區', '龍崎區', '官田區', '麻豆區', '佳里區', '西港區', '七股區', '將軍區', '學甲區', '北門區', '後壁區', '白河區', '東山區', '六甲區', '下營區', '柳營區', '鹽水區', '善化區', '大內區', '山上區', '新市區', '安定區'],
    '高雄市': ['苓雅區', '前鎮區', '旗津區', '鹽埕區', '鼓山區', '左營區', '楠梓區', '三民區', '新興區', '前金區', '鳥松區', '鳳山區', '林園區', '大寮區', '仁武區', '大樹區', '大社區', '路竹區', '阿蓮區', '田寮區', '燕巢區', '橋頭區', '梓官區', '彌陀區', '永安區', '茄萣區', '湖內區', '美濃區', '甲仙區', '杉林區', '六龜區', '茂林區', '桃源區', '那瑪夏區', '小港區', '旗山區', '內門區', '杉林區'],
    '新竹縣': ['竹北市', '竹東鎮', '新埔鎮', '關西鎮', '峨眉鄉', '寶山鄉', '北埔鄉', '橫山鄉', '芎林鄉', '湖口鄉', '新豐鄉', '尖石鄉', '五峰鄉'],
    '苗栗縣': ['苗栗市', '苑裡鎮', '通霄鎮', '竹南鎮', '頭份市', '後龍鎮', '卓蘭鎮', '大湖鄉', '公館鄉', '銅鑼鄉', '南庄鄉', '頭屋鄉', '三義鄉', '西湖鄉', '造橋鄉', '三灣鄉', '獅潭鄉', '泰安鄉'],
    '彰化縣': ['彰化市', '員林市', '和美鎮', '北斗鎮', '田中鎮', '溪湖鎮', '鹿港鎮', '二林鎮', '線西鄉', '伸港鄉', '福興鄉', '秀水鄉', '花壇鄉', '芬園鄉', '大村鄉', '埔鹽鄉', '埔心鄉', '永靖鄉', '社頭鄉', '二水鄉', '田尾鄉', '埤頭鄉', '竹塘鄉', '溪州鄉'],
    '南投縣': ['南投市', '埔里鎮', '草屯鎮', '竹山鎮', '集集鎮', '名間鄉', '鹿谷鄉', '中寮鄉', '魚池鄉', '國姓鄉', '水里鄉', '信義鄉', '仁愛鄉'],
    '雲林縣': ['斗六市', '斗南鎮', '虎尾鎮', '西螺鎮', '土庫鎮', '北港鎮', '古坑鄉', '大埤鄉', '莿桐鄉', '林內鄉', '二崙鄉', '崙背鄉', '麥寮鄉', '台西鄉', '東勢鄉', '褒忠鄉', '四湖鄉', '口湖鄉', '水林鄉', '元長鄉'],
    '嘉義縣': ['太保市', '朴子市', '布袋鎮', '大林鎮', '民雄鄉', '溪口鄉', '新港鄉', '六腳鄉', '東石鄉', '鹿草鄉', '水上鄉', '中埔鄉', '竹崎鄉', '梅山鄉', '番路鄉', '大埔鄉', '阿里山鄉'],
    '屏東縣': ['屏東市', '潮州鎮', '東港鎮', '恆春鎮', '萬丹鄉', '長治鄉', '麟洛鄉', '九如鄉', '里港鄉', '高樹鄉', '鹽埔鄉', '高雄市', '萬巒鄉', '內埔鄉', '竹田鄉', '新埤鄉', '枋寮鄉', '新園鄉', '崁頂鄉', '林邊鄉', '南州鄉', '佳冬鄉', '滿州鄉', '車城鄉', '枋山鄉', '牡丹鄉', '獅子鄉', '春日鄉', '來義鄉', '泰武鄉', '霧台鄉', '瑪家鄉', '三地門鄉'],
    '宜蘭縣': ['宜蘭市', '羅東鎮', '蘇澳鎮', '頭城鎮', '礁溪鄉', '壯圍鄉', '員山鄉', '冬山鄉', '五結鄉', '三星鄉', '大同鄉', '南澳鄉'],
    '花蓮縣': ['花蓮市', '吉安鄉', '新城鄉', '秀林鄉', '鳳林鎮', '光復鄉', '豐濱鄉', '瑞穗鄉', '玉里鎮', '富里鄉', '卓溪鄉', '萬榮鄉'],
    '台東縣': ['台東市', '成功鎮', '關山鎮', '卑南鄉', '鹿野鄉', '延平鄉', '東河鄉', '長濱鄉', '池上鄉', '海端鄉', '關山鎮', '延平鄉', '太麻里鄉', '金峰鄉', '達仁鄉', '大武鄉', '綠島鄉', '蘭嶼鄉']
};

/**
 * 根據選擇的縣市更新鄉鎮市區下拉選單
 * @param {HTMLSelectElement} citySelect - 縣市選擇器（可選，若未提供則使用 ID）
 */
function updateDistricts(citySelect) {
    const citySelectElement = citySelect || document.getElementById('city');
    const districtSelect = document.getElementById('district');
    const selectedCity = citySelectElement.value;

    districtSelect.innerHTML = '<option value="">請選擇</option>';

    if (selectedCity && districts[selectedCity]) {
        districts[selectedCity].forEach(district => {
            const option = document.createElement('option');
            option.value = district;
            option.textContent = district;
            districtSelect.appendChild(option);
        });
    } else {
        districtSelect.innerHTML = '<option value="">請先選擇縣市</option>';
    }
}

/* --------------------------------------------------------------------------
   3. 表單輔助函式
   -------------------------------------------------------------------------- */

/**
 * 啟用表單中所有 input、select、textarea 的編輯
 * @param {HTMLFormElement} form - 表單元素
 */
function enableForm(form) {
    form.querySelectorAll("input").forEach(input => {
        input.disabled = false;
    });
    form.querySelectorAll("select").forEach(input => {
        input.disabled = false;
    });
    form.querySelectorAll("textarea").forEach(input => {
        input.disabled = false;
    });
}

/**
 * 停用表單中所有 input、select、textarea 的編輯
 * @param {HTMLFormElement} form - 表單元素
 */
function disableForm(form) {
    form.querySelectorAll("input").forEach(input => {
        input.disabled = true;
    });
    form.querySelectorAll("select").forEach(input => {
        input.disabled = true;
    });
    form.querySelectorAll("textarea").forEach(input => {
        input.disabled = true;
    });
}

/**
 * 清空表單中所有非 hidden 欄位的值
 * @param {HTMLFormElement} form - 表單元素
 */
function clearForm(form) {
    form.querySelectorAll("input").forEach(input => {
        if (input.type !== "hidden") {
            input.value = '';
        }
    });
    form.querySelectorAll("select").forEach(input => {
        if (input.type !== "hidden") {
            input.value = '';
        }
    });
    form.querySelectorAll("textarea").forEach(input => {
        if (input.type !== "hidden") {
            input.value = '';
        }
    });
}

/* --------------------------------------------------------------------------
   4. 檢查紀錄相關函式
   -------------------------------------------------------------------------- */


/**
 * 進入檢查編輯模式
 * @param {string} exam_id - 檢查項目 ID
 */
function checkButton(exam_id) {
    const form = document.getElementById(`exam-${exam_id}`);
    enableForm(form);
    clearForm(form);
    document.getElementById(`exam-checkbutton-${exam_id}`).classList.add("hidden");
    document.getElementById(`exam-savebutton-${exam_id}`).classList.remove("hidden");
    document.getElementById(`exam-cancelbutton-${exam_id}`).classList.remove("hidden");
}

/**
 * 取消檢查編輯，重新載入頁面
 */
function cancelButton() {
    location.reload();
}

/* --------------------------------------------------------------------------
   5. 病患詳細頁面函式
   -------------------------------------------------------------------------- */

/**
 * 切換病患資訊表單的編輯模式
 */
function toggleInfoForm() {
    const info_form = document.getElementById("info-form");
    document.getElementById("info-form-menu-button").classList.toggle("hidden");
    document.getElementById("info-form-menu-button").classList.toggle("inline-block");
    document.getElementById("info-form-menu-button-enabled").classList.toggle("hidden");
    document.getElementById("info-form-menu-button-enabled").classList.toggle("inline-block");
    info_form.querySelectorAll("input").forEach(input => {
        if (input.disabled) {
            input.disabled = false;
            if (input.value === "-") {
                input.value = "";
            }
        } else {
            input.disabled = true;
            if (input.value === "") {
                input.value = "-";
            }
        }
    });
    info_form.querySelectorAll("select").forEach(select => {
        if (select.disabled) {
            select.disabled = false;
        } else {
            select.disabled = true;
        }
    });
}

/**
 * 切換顯示用藥區塊和新增用藥表單
 */
function toggleAddMedicine() {
    const showInfo = document.getElementById("show-medicine-info");
    const addInfo = document.getElementById("add-medicine-info");
    showInfo.classList.toggle("hidden");
    addInfo.classList.toggle("hidden");
}

/**
 * 切換顯示回診記錄表單
 */
function toggleAddFollowupRecord() {
    const followupRecordForm = document.getElementById("add-followup-record-form");
    const medicineButtonMenu = document.getElementById("medicine-button-menu");
    const followupRecordButtonMenu = document.getElementById("followup-record-button-menu");
    followupRecordForm.classList.toggle("hidden");
    medicineButtonMenu.classList.toggle("hidden");
    followupRecordButtonMenu.classList.toggle("hidden");
}

/* --------------------------------------------------------------------------
   6. 管理頁面函式
   -------------------------------------------------------------------------- */

/**
 * 刪除管理項目（軟刪除）
 * @param {string} type - 項目類型：doctors, diseases, examinations, tradmedicines, biomedicines
 * @param {number} id - 項目 ID
 */
function deleteCard(type, id) {
    let url;
    if (type === "doctors") {
        url = "/api/delete/doctor";
    } else if (type === "diseases") {
        url = "/api/delete/disease";
    } else if (type === "examinations") {
        url = "/api/delete/examination";
    } else if (type === "tradmedicines" || type === "biomedicines") {
        url = "/api/delete/medicine";
    }
    
    fetch(url, {
        method: "DELETE",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ id, type })
    }).then(
        response => response.json()
    ).then(
        data => {
            if (data.success) {
                alert("刪除成功");
                location.reload();
            } else {
                alert("刪除失敗");
            }
        }
    ).catch(
        error => {
            console.error("Error", error);
            alert("刪除失敗，請稍後再試");
        }
    );
}

/**
 * 切換顯示新增表單卡片
 */
function toggleAddCard() {
    const buttonAdd = document.getElementById("button-add");
    const cardAdd = document.getElementById("card-add");
    buttonAdd.classList.toggle("hidden");
    cardAdd.classList.toggle("hidden");
    document.querySelectorAll("input").forEach(input => input.value = "");
    document.querySelectorAll("select").forEach(select => {
        select.value = "";
        select.dispatchEvent(new Event("change"));
    });
}

/**
 * 藥物類型選擇時的處理
 * 控制顯示不同的輸入欄位
 */
function selectMedicineType() {
    const selectMedicineType = document.getElementById("select-medicine-type");
    const followupInterval = document.getElementById("input-interval");
    const firstApplyDose = document.getElementById("first-apply-dose");
    const continueApplyDose = document.getElementById("continue-apply-dose");
    
    followupInterval.classList.add("hidden");
    firstApplyDose.classList.add("hidden");
    continueApplyDose.classList.add("hidden");
    
    if (selectMedicineType.value === "傳統用藥") {
        followupInterval.classList.remove("hidden");
    } else if (selectMedicineType.value === "生物製劑") {
        firstApplyDose.classList.remove("hidden");
        continueApplyDose.classList.remove("hidden");
    }
}

/* --------------------------------------------------------------------------
   7. 歷史紀錄頁面函式
   -------------------------------------------------------------------------- */

/**
 * 刪除用藥歷史記錄
 * @param {string} id - 記錄 ID
 * @param {string} type - 記錄類型：traditional, biological
 */
function deleteHistory(id, type) {
    if (!confirm("確定要刪除?")) {
        return;
    }
    const formData = new FormData();
    formData.append("id", id);
    formData.append("type", type);
    
    fetch("/api/delete/history", {
        method: "DELETE",
        body: formData
    }).then(response => response.json()).then(data => {
        if (data.success === false) {
            return false;
        }
    });
    alert("更新成功!");
    location.reload();
}

/**
 * 儲存所有歷史記錄
 */
function save() {
    if (!confirm("確定要更新?")) {
        location.reload();
        return;
    }
    const forms = document.querySelectorAll("form");
    for (let index = 0; index < forms.length; index++) {
        const form = forms[index];
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
    }
    for (let index = 0; index < forms.length; index++) {
        const form = forms[index];
        if (!saveForm(form)) {
            alert(`保存第${index + 1}紀錄失敗`);
            location.reload();
            return;
        }
    }
    location.reload();
}

/**
 * 儲存單個歷史記錄表單
 * @param {HTMLFormElement} form - 表單元素
 * @returns {boolean} 是否成功
 */
function saveForm(form) {
    fetch("/api/update/history", {
        method: "POST",
        body: new FormData(form)
    }).then(response => response.json()).then(data => {
        if (data.success === false) {
            return false;
        }
    });
    return true;
}

/**
 * 啟用歷史記錄編輯模式
 */
function enableEditing() {
    const forms = document.querySelectorAll("form");
    const saveButton = document.getElementById("save-button");
    const enableButton = document.getElementById("enable-button");
    
    saveButton.classList.toggle("hidden");
    saveButton.classList.toggle("inline-block");
    enableButton.classList.toggle("hidden");
    enableButton.classList.toggle("inline-block");
    
    for (let index = 0; index < forms.length; index++) {
        const form = forms[index];
        form.querySelectorAll("input").forEach(input => {
            if (input.disabled) {
                input.disabled = false;
            } else {
                input.disabled = true;
            }
        });
        form.querySelectorAll("textarea").forEach(input => {
            if (input.disabled) {
                input.disabled = false;
            } else {
                input.disabled = true;
            }
        });
        form.querySelectorAll("select").forEach(input => {
            if (input.disabled) {
                input.disabled = false;
            } else {
                input.disabled = true;
            }
        });
    }
}

/* --------------------------------------------------------------------------
   8. 表單提交鎖定
   -------------------------------------------------------------------------- */

/**
 * 防止表單重複提交 - 在表單提交時禁用按鈕
 */
document.addEventListener("DOMContentLoaded", () => {
    // 側邊欄狀態初始化
    const sidebar = document.getElementById("sidebar");
    if (sidebar) {
        const isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
        if (isCollapsed) {
            toggleSidebar();
        }
    }

    // 自動為所有 form 表單添加提交鎖定
    document.querySelectorAll("form").forEach(form => {
        form.addEventListener("submit", function(e) {
            // 檢查表單是否有效
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }

            // 禁用表單中的所有提交按鈕
            form.querySelectorAll('button[type="submit"], input[type="submit"], a[class*="btn"]').forEach(btn => {
                btn.disabled = true;
                btn.dataset.originalText = btn.textContent;
                btn.textContent = "處理中...";
            });

            // 2秒後自動恢復（防止網路問題造成永久鎖定）
            setTimeout(() => {
                form.querySelectorAll('button[type="submit"], input[type="submit"], a[class*="btn"]').forEach(btn => {
                    btn.disabled = false;
                    if (btn.dataset.originalText) {
                        btn.textContent = btn.dataset.originalText;
                    }
                });
            }, 2000);
        });
    });
});

/**
 * 通用 API 提交函式，帶有防止重複提交的鎖定
 * @param {string} url - API 端點
 * @param {Object} options - fetch 選項
 * @returns {Promise}
 */
async function apiSubmit(url, options = {}) {
    // 防止重複提交
    if (window._apiSubmitting) {
        return { success: false, message: "正在處理中，請稍候" };
    }
    window._apiSubmitting = true;

    try {
        const response = await fetch(url, options);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error("API 錯誤:", error);
        return { success: false, message: "網路錯誤，請稍後再試" };
    } finally {
        // 延遲解除鎖定，防止快速點擊
        setTimeout(() => {
            window._apiSubmitting = false;
        }, 1000);
    }
}
