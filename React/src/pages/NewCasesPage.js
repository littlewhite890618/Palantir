import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Construction } from 'lucide-react';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🚧 VIBE: 這是通知鈴鐺點下去的目的地，目前只是占位頁。
//    N1（通知鈴鐺）的邊界只到「有這個入口、點得下去」；真正列出新增補助案
//    的清單內容是 N2 的工作。之後 N2 只要把這個檔案的內容換掉就好，
//    路由、判斷條件、檔案位置都不用動，鈴鐺那邊的連結也不用改。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function NewCasesPage() {
  const navigate = useNavigate();

  return (
    <div className="page-container">
      <button
        onClick={() => navigate(-1)}
        style={{
          display: 'flex', alignItems: 'center', gap: '4px',
          border: 'none', background: 'transparent', cursor: 'pointer',
          color: '#1a73e8', fontSize: '14px', padding: '8px 0', marginTop: '24px',
        }}
      >
        <ChevronLeft size={16} strokeWidth={1.75} /> 返回
      </button>

      <div style={{ textAlign: 'center', marginTop: '80px', color: '#9ca3af' }}>
        <Construction size={40} strokeWidth={1.5} />
        <h2 style={{ fontSize: '18px', color: '#6b7280', margin: '16px 0 8px' }}>
          功能開發中
        </h2>
        <p style={{ fontSize: '14px', lineHeight: '1.7' }}>
          新增補助案的清單畫面還在製作中，<br />完成後這裡會列出所有通過審核的新案。
        </p>
      </div>
    </div>
  );
}

export default NewCasesPage;
