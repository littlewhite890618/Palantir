import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Heart, LogOut } from 'lucide-react';
import { lock, getExportedAt } from '../services/subsidyService';

const navStyle = {
  backgroundColor: '#fff',
  padding: '0 24px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  borderBottom: '1px solid #e5e7eb',
  height: '60px',
  position: 'sticky',
  top: 0,
  zIndex: 100,
};

function Navbar() {
  const location = useLocation();

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 🔒 VIBE: 系統沒有真正的登入帳號機制，只有「記住的解密密碼」。
  //    這顆按鈕的行為是登出（清除記住的密碼），文字/icon 直接標「登出」，
  //    不再用容易誤會成「個人設定」的「帳號」字樣（2026-09-29 調整）。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const handleLogoutClick = () => {
    if (!window.confirm('登出後下次進入需要重新輸入密碼，確定要登出嗎？')) return;
    lock();
    window.location.reload();
  };

  const exportedAt = getExportedAt();

  return (
    <nav className="navbar" style={navStyle}>

      {/* 左側：純文字 Logo，不用裝飾 icon */}
      <Link to="/" style={{ textDecoration: 'none' }}>
        <span style={{
          fontWeight: '700',
          fontSize: '19px',
          color: '#1a1a1a',
          letterSpacing: '-0.2px',
        }}>
          Palantir
        </span>
      </Link>

      {/* 右側：資料更新時間（極低存在感）+ 收藏 + 登出。
          窄螢幕（<480px）時文字標籤自動隱藏，只留 icon（見 App.css）。 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
        {exportedAt && (
          <span className="navbar-exported" style={{ fontSize: '12px', color: '#9ca3af', marginRight: '12px' }}>
            資料更新於 {new Date(exportedAt).toLocaleDateString('zh-TW')}
          </span>
        )}

        <Link to="/favorites" style={{ textDecoration: 'none' }}>
          <button
            className={`navbar-icon-btn${location.pathname === '/favorites' ? ' active' : ''}`}
            title="我的收藏"
          >
            <Heart size={18} strokeWidth={1.75} />
            <span className="nav-icon-label">我的收藏</span>
          </button>
        </Link>

        <button onClick={handleLogoutClick} className="navbar-icon-btn" title="登出">
          <LogOut size={18} strokeWidth={1.75} />
          <span className="nav-icon-label">登出</span>
        </button>
      </div>
    </nav>
  );
}

export default Navbar;
