import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 管理台是後台工作的地方，跟給顧問用的補助案搜尋器是兩種使用情境，
//    所以不共用 Navbar——搜尋器那邊完全不會出現任何通往這裡的入口。
//    整個管理台只在本機開發模式存在（見 App.js）。
//    Topbar 改版（2026-09-30）：改用淺色，跟搜尋器 Navbar 質感一致；
//    刻意不加通知鈴鐺、不加「管理員」帳號下拉——這裡只有管理員一人在用，
//    那些是給多人使用情境設計的，現階段加了也沒有實際功能。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const barStyle = {
  backgroundColor: '#fff',
  color: '#1a1a1a',
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

function AdminLayout() {
  return (
    <>
      <div style={barStyle}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', minWidth: 0 }}>
          <span style={{ fontWeight: 700, fontSize: '19px', letterSpacing: '-0.2px' }}>
            Palantir
          </span>
          <span className="admin-subtitle" style={{ fontSize: '13px', color: '#9ca3af' }}>
            管理台
          </span>
        </div>

        {/* 本機模式下搜尋器就在同一個 app 裡，留一條路回去，不用自己改網址 */}
        <Link to="/" className="admin-back">
          <ArrowLeft size={15} strokeWidth={1.75} /> 回搜尋器
        </Link>
      </div>

      <Outlet />
    </>
  );
}

export default AdminLayout;
