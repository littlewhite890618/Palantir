import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Heart, User } from 'lucide-react';
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
  //    這裡的「帳號」icon 沿用原本登出（清除記住的密碼）的行為，
  //    只是換個更貼近設計稿（user icon）的外觀呈現，功能不變。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const handleAccountClick = () => {
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

      {/* 右側：資料更新時間（極低存在感）+ 收藏 + 帳號。
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

        <button onClick={handleAccountClick} className="navbar-icon-btn" title="帳號">
          <User size={18} strokeWidth={1.75} />
          <span className="nav-icon-label">帳號</span>
        </button>
      </div>
    </nav>
  );
}

export default Navbar;
