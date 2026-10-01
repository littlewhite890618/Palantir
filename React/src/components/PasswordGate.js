import React, { useState, useEffect } from 'react';
import { Lock } from 'lucide-react';
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
      <div className="page-container"><div className="state-block">載入中…</div></div>
    );
  }

  //已經解鎖，直接顯示子元件
  if (unlocked) return children;

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      padding: '24px',
      background: 'var(--paper)',
    }}>
      {/* 靠左、不置中：這是一道公務性質的門，不是行銷首頁。
          左側粗墨條 + 宋體抬頭，延續全站的卷宗語彙。 */}
      <form
        onSubmit={handleSubmit}
        style={{
          width: '100%',
          maxWidth: '400px',
          margin: '0 auto',
          borderLeft: '3px solid var(--seal)',
          paddingLeft: '26px',
        }}
      >
        <h1 style={{ fontSize: '30px', marginBottom: '10px' }}>Palantir</h1>

        {/* 系統沒有帳號機制，只有一組共用密碼（PBKDF2+AES-GCM）。
            文案照實際行為寫「密碼」，不寫「帳號」，避免讓人誤以為有個人登入。 */}
        <p style={{ fontSize: '14.5px', color: 'var(--ink-70)', marginBottom: '26px', maxWidth: '30ch' }}>
          政府補助案查詢系統。輸入密碼後即可檢視補助案資料。
        </p>

        <label
          htmlFor="gate-password"
          style={{ display: 'block', fontSize: '12px', color: 'var(--ink-45)', marginBottom: '6px' }}
        >
          密碼
        </label>

        <div style={{ position: 'relative', marginBottom: '12px' }}>
          <Lock
            size={16}
            strokeWidth={2}
            style={{
              position: 'absolute', left: '13px', top: '50%',
              transform: 'translateY(-50%)', color: 'var(--ink-25)', pointerEvents: 'none',
            }}
          />
          <input
            id="gate-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
            disabled={busy}
            className="field"
            style={{
              paddingLeft: '38px',
              borderColor: error ? 'var(--vermilion)' : 'var(--rule-strong)',
            }}
          />
        </div>

        {/* 錯誤訊息佔固定高度，出現時表單不會跳動 */}
        <div style={{ minHeight: '22px', fontSize: '13px', color: 'var(--vermilion)', marginBottom: '10px' }}>
          {error}
        </div>

        <button
          type="submit"
          disabled={busy || !password.trim()}
          className="btn btn-primary"
          style={{ width: '100%', padding: '13px' }}
        >
          {/* 🔐 PBKDF2 刻意設計成慢的（約 0.2 秒），加上解壓縮會再久一點。
              沒有這個狀態提示，使用者會以為按鈕沒反應而重複點擊。 */}
          {busy ? '解密中…' : '解鎖'}
        </button>

        <p style={{ fontSize: '12px', color: 'var(--ink-25)', marginTop: '20px' }}>
          忘記密碼請洽系統管理員
        </p>
      </form>
    </div>
  );
}

export default PasswordGate;
