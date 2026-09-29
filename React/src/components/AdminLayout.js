import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 管理台是後台工作的地方，跟給顧問用的補助案搜尋器是兩種使用情境，
//    所以不共用 Navbar——搜尋器那邊完全不會出現任何通往這裡的入口。
//    深色標題列是刻意的：一眼就知道「現在不在搜尋器裡」，不會誤以為在改前台資料。
//    整個管理台只在本機開發模式存在（見 App.js）。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const barStyle = {
  backgroundColor: '#1f2937',
  color: '#f9fafb',
  padding: '0 24px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  height: '56px',
  position: 'sticky',
  top: 0,
  zIndex: 100,
};

function AdminLayout() {
  return (
    <>
      <div style={barStyle}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', minWidth: 0 }}>
          <span style={{ fontWeight: 700, fontSize: '16px', letterSpacing: '-0.2px' }}>
            Palantir 管理台
          </span>
          <span className="admin-subtitle" style={{ fontSize: '13px', color: '#9ca3af' }}>
            新案審核
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
