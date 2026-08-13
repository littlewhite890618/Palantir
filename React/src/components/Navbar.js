import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { lock, getExportedAt } from '../services/subsidyService';

const navStyle = {
  backgroundColor: '#fff',
  padding: '0 40px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  height: '64px',
  position: 'sticky',
  top: 0,
  zIndex: 100,
};

function Navbar() {
  const location = useLocation();

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 🔒 VIBE: 登出＝忘記這台機器記住的密碼。
  //    平常密碼是永久記住的（1-3 人偶爾用，每次都要輸會讓人乾脆不用），
  //    這顆按鈕是給「要換密碼」或「這台電腦要借人」時的保險。
  //    reload 是刻意的——最乾淨地把已解密的資料從記憶體清掉，
  //    回到 PasswordGate 的初始狀態。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const handleLock = () => {
    if (!window.confirm('登出後下次進入需要重新輸入密碼，確定要登出嗎？')) return;
    lock();
    window.location.reload();
  };

  const exportedAt = getExportedAt();

  return (
    <nav style={navStyle}>

      {/* 左側：Palentir + 所有補助案 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

        {/* Palentir 按鈕（搜尋頁） */}
        <Link to="/" style={{ textDecoration: 'none' }}>
          <div style={{
            fontWeight: '700',
            fontSize: '20px',
            color: location.pathname === '/' ? '#1a73e8' : '#555',
            cursor: 'pointer',
            transition: 'color 0.2s',
            letterSpacing: '0.5px',
            padding: '8px 12px',
          }}>
            🧭 Palantir
          </div>
        </Link>

   
      </div>

      {/* 右側：資料時間 + 收藏 + 登出 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>

        {/* 📌 資料匯出時間——這個站的資料是排程推上來的快照，不是即時的，
            讓使用者知道自己看的是什麼時候的資料 */}
        {exportedAt && (
          <span style={{ fontSize: '12px', color: '#aaa', marginRight: '8px' }}>
            資料更新於 {new Date(exportedAt).toLocaleDateString('zh-TW')}
          </span>
        )}

        {/* 收藏入口 */}
        <Link to="/favorites" style={{ textDecoration: 'none' }}>
          <button
            style={{
              border: 'none',
              background: location.pathname === '/favorites' ? 'rgba(26, 115, 232, 0.1)' : 'transparent',
              cursor: 'pointer',
              fontSize: '20px',
              padding: '8px 10px',
              borderRadius: '8px',
              transition: 'background 0.2s',
            }}
            title="我的收藏"
          >
            ❤️
          </button>
        </Link>

        {/* 登出（清除記住的密碼） */}
        <button
          onClick={handleLock}
          style={{
            border: 'none',
            background: 'transparent',
            cursor: 'pointer',
            fontSize: '18px',
            padding: '8px 10px',
            borderRadius: '8px',
            transition: 'background 0.2s',
          }}
          title="登出（清除記住的密碼）"
        >
          🔒
        </button>

      </div>
    </nav>
  );
}

export default Navbar;