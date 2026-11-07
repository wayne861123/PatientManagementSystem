/**
 * 系統設定頁面 - 版本更新與資料備份
 */

function showMessage(elId, text, isError) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = text;
    el.classList.remove('hidden');
    el.classList.toggle('msg-error', !!isError);
    el.classList.toggle('msg-ok', !isError);
}

function checkUpdate() {
    const btn = document.getElementById('btn-check-update');
    if (btn) btn.textContent = '檢查中...';
    fetch("/api/check/update")
        .then(r => r.json())
        .then(data => {
            if (btn) btn.textContent = '檢查更新';
            if (data.error) {
                showMessage('update-message', '檢查失敗：' + data.error, true);
                return;
            }
            const latest = document.getElementById('latest-version');
            if (latest) latest.textContent = data.latest || '無';
            const upd = document.getElementById('btn-do-update');
            if (data.has_update) {
                showMessage('update-message', '有新版本可用：' + data.latest, false);
                if (upd) upd.disabled = false;
            } else {
                showMessage('update-message', '已是最新版本', false);
                if (upd) upd.disabled = true;
            }
        })
        .catch(e => {
            if (btn) btn.textContent = '檢查更新';
            showMessage('update-message', '檢查失敗：' + e, true);
        });
}

function doUpdate() {
    if (!confirm('確定要下載並安裝更新嗎？\n\n更新前會自動建立資料庫備份。\n安裝後需要重新啟動程式。')) {
        return;
    }
    const btn = document.getElementById('btn-do-update');
    if (btn) {
        btn.textContent = '更新中...';
        btn.disabled = true;
    }
    fetch("/api/apply/update", { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (btn) {
                btn.textContent = '下載並安裝更新';
                btn.disabled = false;
            }
            showMessage('update-message',
                data.success ? data.message : ('更新失敗：' + data.message), !data.success);
        })
        .catch(e => {
            if (btn) {
                btn.textContent = '下載並安裝更新';
                btn.disabled = false;
            }
            showMessage('update-message', '更新失敗：' + e, true);
        });
}

function createBackup() {
    showMessage('backup-message', '建立備份中...', false);
    fetch("/api/backup/create", { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showMessage('backup-message', '備份已建立', false);
                setTimeout(() => location.reload(), 1200);
            } else {
                showMessage('backup-message', '建立失敗：' + data.message, true);
            }
        })
        .catch(e => showMessage('backup-message', '建立失敗：' + e, true));
}

function checkIntegrity() {
    showMessage('backup-message', '檢查中...', false);
    fetch("/api/backup/check")
        .then(r => r.json())
        .then(data => {
            const el = document.getElementById('integrity-status');
            if (el) el.textContent = data.ok ? '正常' : ('異常：' + data.message);
            showMessage('backup-message',
                data.ok ? '資料庫完整性正常' : ('資料庫異常：' + data.message), !data.ok);
        })
        .catch(e => showMessage('backup-message', '檢查失敗：' + e, true));
}

function restoreBackup(name) {
    if (!confirm('確定要從備份 ' + name + ' 還原嗎？\n\n目前的資料會先被自動備份一次。\n還原後需要重新啟動程式。')) {
        return;
    }
    showMessage('backup-message', '還原中...', false);
    fetch("/api/backup/restore", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showMessage('backup-message', data.message, false);
                setTimeout(() => location.reload(), 1500);
            } else {
                showMessage('backup-message', '還原失敗：' + data.message, true);
            }
        })
        .catch(e => showMessage('backup-message', '還原失敗：' + e, true));
}

// 載入時自動取得資料庫完整性狀態
document.addEventListener('DOMContentLoaded', function () {
    fetch("/api/backup/check")
        .then(r => r.json())
        .then(data => {
            const el = document.getElementById('integrity-status');
            if (el) el.textContent = data.ok ? '正常' : ('異常：' + data.message);
        });
});
