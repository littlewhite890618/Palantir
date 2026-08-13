import React, { useState, useEffect } from 'react';
import { unlock, unlockWithStored, hasStoredPassword } from '../services/subsidyService';

// PasswordGate 元件負責在使用者輸入正確密碼前，顯示一个輸入密碼的畫面來阻擋對補助案資料的存取。
function PasswordGate({ children }) {
  //密碼解鎖狀態、使用者輸入的密碼、忙碌狀態、錯誤訊息、是否正在檢查記住的密碼
  const [unlocked, setUnlocked] = useState(false);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  // 開場先用記住的密碼試解一次，這段期間不要閃過密碼畫面
  const [checking, setChecking] = useState(() => hasStoredPassword());

  //已經登入過的使用者，或瀏覽器記住了密碼，會自動解鎖
  useEffect(() => {
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
      background: '#f7f8fa',
      padding: '20px',
    }}>
      <form
        onSubmit={handleSubmit}
        style={{
          background: 'white',
          padding: '40px 36px',
          borderRadius: '16px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
          width: '100%',
          maxWidth: '380px',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: '32px', marginBottom: '8px' }}>🧭</div>
        <h1 style={{ fontSize: '20px', fontWeight: '700', color: '#333', marginBottom: '6px' }}>
          Palantir
        </h1>
        <p style={{ fontSize: '14px', color: '#888', marginBottom: '28px' }}>
          請輸入密碼以檢視補助案資料
        </p>
      //輸入密碼的欄位，若有錯誤訊息則顯示紅色邊框
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="密碼"
          autoFocus
          disabled={busy}
          style={{
            width: '100%',
            padding: '13px 16px',
            fontSize: '15px',
            border: error ? '1.5px solid #e53935' : '1.5px solid #ddd',
            borderRadius: '10px',
            outline: 'none',
            marginBottom: '14px',
            boxSizing: 'border-box',
            transition: 'border-color 0.2s',
          }}
        />

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
            padding: '13px',
            fontSize: '15px',
            fontWeight: '600',
            color: 'white',
            background: busy || !password.trim() ? '#b9c9e8' : '#1a73e8',
            border: 'none',
            borderRadius: '10px',
            cursor: busy || !password.trim() ? 'not-allowed' : 'pointer',
            transition: 'background 0.2s',
          }}
        >
          {/* 🔐 PBKDF2 刻意設計成慢的（約 0.2 秒），加上解壓縮會再久一點。
              沒有這個狀態提示，使用者會以為按鈕沒反應而重複點擊。 */}
          {busy ? '解密中...' : '進入'}
        </button>
      </form>
    </div>
  );
}

export default PasswordGate;
