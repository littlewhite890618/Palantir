import React, { useState, useEffect } from 'react';
import { Lock, ArrowRight } from 'lucide-react';
import { unlock, unlockWithStored, hasStoredPassword, LOCAL_API_URL } from '../services/subsidyService';

// PasswordGate 元件負責在使用者輸入正確密碼前，顯示一个輸入密碼的畫面來阻擋對補助案資料的存取。
function PasswordGate({ children }) {
  // Hooks 一律要在最上面無條件呼叫（React 規則），本機開發模式的提前放行要放在
  // 所有 Hooks 宣告「之後」，不能放在前面直接 return——那樣會讓 Hooks 呼叫次數
  // 依條件變動，違反 Rules of Hooks。

  //密碼解鎖狀態、使用者輸入的密碼、忙碌狀態、錯誤訊息、是否正在檢查記住的密碼
  const [unlocked, setUnlocked] = useState(false);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  // 開場先用記住的密碼試解一次，這段期間不要閃過密碼畫面；本機開發模式不用密碼流程，
  // 不需要這段「檢查中」的狀態。
  const [checking, setChecking] = useState(() => !LOCAL_API_URL && hasStoredPassword());

  //已經登入過的使用者，或瀏覽器記住了密碼，會自動解鎖（本機開發模式跳過整段）
  useEffect(() => {
    if (LOCAL_API_URL) return;
    if (!hasStoredPassword()) return;

    let cancelled = false;
    unlockWithStored()
      .then(() => {
        if (!cancelled) { setUnlocked(true); setChecking(false); }
      })
      .catch(() => {
        if (!cancelled) {
          setError('資料已更新，請重新輸入密碼');
          setChecking(false);
        }
      });
    return () => { cancelled = true; };
  }, []);
  
  //手動輸入密碼解鎖
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!password.trim() || busy) return;

    setBusy(true);
    setError('');
    try {
      await unlock(password);
      setUnlocked(true);
    } catch (err) {
      console.error('解鎖失敗:', err);
      setError('密碼錯誤，或資料檔無法讀取');
      setPassword('');
    } finally {
      setBusy(false);
    }
  };

  // 本機開發模式（LOCAL_API_URL 有設）：資料本來就沒加密，密碼畫面沒有意義，直接放行。
  if (LOCAL_API_URL) return children;

  // 用記住的密碼自動解鎖中——空白畫面比閃一下密碼框好
  if (checking) {
    return (
      <div style={{ textAlign: 'center', marginTop: '160px', color: '#888' }}>
        載入中...
      </div>
    );
  }

  //已經解鎖，直接顯示子元件
  if (unlocked) return children;

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      // 淺色漸層背景（比照參考風格），跟表單卡片的純白拉出層次
      background: 'linear-gradient(160deg, #eef4fd 0%, #f7f9fc 45%, #ffffff 100%)',
      padding: '20px',
    }}>
      <form
        onSubmit={handleSubmit}
        style={{
          width: '100%',
          maxWidth: '360px',
          textAlign: 'center',
        }}
      >
        <h1 style={{ fontSize: '34px', fontWeight: '800', color: '#111827', letterSpacing: '-0.5px', marginBottom: '10px' }}>
          Palantir
        </h1>
        {/* 系統沒有帳號機制，只有一組共用密碼（PBKDF2+AES-GCM）。
            文案照實際行為寫「密碼」，不寫參考風格圖裡的「帳號」，避免讓人誤以為有個人登入。 */}
        <p style={{ fontSize: '14px', color: '#6b7280', lineHeight: '1.6', marginBottom: '28px' }}>
          請輸入密碼，驗證後即可開始使用<br />AI 政府補助搜尋服務
        </p>

        <div style={{ height: '1px', background: '#e5e7eb', marginBottom: '28px' }} />

        {/* 輸入密碼的欄位，若有錯誤訊息則顯示紅色邊框 */}
        <div style={{ position: 'relative', marginBottom: '14px' }}>
          <Lock
            size={17}
            strokeWidth={1.75}
            style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }}
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="請輸入密碼"
            autoFocus
            disabled={busy}
            style={{
              width: '100%',
              padding: '15px 16px 15px 44px',
              fontSize: '15px',
              border: error ? '1.5px solid #e53935' : '1px solid #e5e7eb',
              borderRadius: '999px',
              outline: 'none',
              boxSizing: 'border-box',
              background: '#fff',
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
              transition: 'border-color 0.2s',
            }}
          />
        </div>

        {/* 錯誤訊息佔一個固定高度，避免出現時整個表單跳動 */}
        <div style={{
          minHeight: '20px',
          fontSize: '13px',
          color: '#e53935',
          marginBottom: '10px',
        }}>
          {error}
        </div>

        <button
          type="submit"
          disabled={busy || !password.trim()}
          style={{
            width: '100%',
            padding: '15px',
            fontSize: '15px',
            fontWeight: '600',
            color: 'white',
            background: busy || !password.trim() ? '#b9c9e8' : '#1a73e8',
            border: 'none',
            borderRadius: '999px',
            cursor: busy || !password.trim() ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            transition: 'background 0.2s',
          }}
        >
          {/* 🔐 PBKDF2 刻意設計成慢的（約 0.2 秒），加上解壓縮會再久一點。
              沒有這個狀態提示，使用者會以為按鈕沒反應而重複點擊。 */}
          {busy ? '解密中...' : (<>解鎖 <ArrowRight size={16} strokeWidth={2} /></>)}
        </button>

        {/* 參考風格圖底部是「服務條款／隱私政策」連結，但這是內部工具、沒有這些頁面，
            放假連結會誤導人。換成真正有用的一句：密碼忘記時該找誰。 */}
        <p style={{ fontSize: '12px', color: '#9ca3af', marginTop: '24px' }}>
          忘記密碼請洽系統管理員
        </p>
      </form>
    </div>
  );
}

export default PasswordGate;
