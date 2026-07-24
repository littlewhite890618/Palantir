import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

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
  const [showNotification, setShowNotification] = useState(false);
  // 📌 showNotification 是用來控制通知視窗要不要顯示
  // true = 顯示，false = 隱藏

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
            🧭 Palentir
          </div>
        </Link>

   
      </div>

      {/* 右側：通知鈴鐺 */}
      <div style={{ position: 'relative' }}>

        {/* 鈴鐺按鈕 */}
        <button
          onClick={() => setShowNotification(!showNotification)}
          // 📌 點一下顯示，再點一下隱藏，就是切換 true/false
          style={{
            border: 'none',
            background: showNotification ? 'rgba(26, 115, 232, 0.1)' : 'transparent',
            cursor: 'pointer',
            fontSize: '22px',
            padding: '8px 10px',
            borderRadius: '8px',
            transition: 'background 0.2s',
            position: 'relative',
          }}
        >
          🔔
          {/* 未讀紅點 */}
          <span style={{
            position: 'absolute',
            top: '6px',
            right: '6px',
            width: '8px',
            height: '8px',
            background: '#e53935',
            borderRadius: '50%',
            border: '1.5px solid white',
            // 📌 這是鈴鐺右上角的小紅點，代表有未讀通知
          }} />
        </button>

        {/* 通知下拉視窗 */}
        {showNotification && (
          <div style={{
            position: 'absolute',
            top: '52px',
            right: '0',
            width: '300px',
            background: 'white',
            borderRadius: '12px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            border: '1px solid #eee',
            overflow: 'hidden',
            zIndex: 200,
            // 📌 position absolute 讓視窗浮在鈴鐺按鈕正下方
          }}>

            {/* 通知視窗標題 */}
            <div style={{
              padding: '14px 18px',
              borderBottom: '1px solid #f0f0f0',
              fontWeight: '600',
              fontSize: '15px',
              color: '#333',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <span>通知</span>
              <span style={{ fontSize: '12px', color: '#1a73e8', fontWeight: '400', cursor: 'pointer' }}>
                全部已讀
              </span>
            </div>

          {/* 通知內容 */}
            <div style={{
              padding: '20px 18px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}>
              {/* 未讀藍點 */}
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#1a73e8',
                flexShrink: 0,
              }} />
              <p style={{ fontSize: '14px', color: '#333', fontWeight: '500' }}>
                有 3 筆新的補助案！
              </p>
            </div>

          </div>
        )}

        {/* 點擊其他地方關閉通知視窗 */}
        {showNotification && (
          <div
            onClick={() => setShowNotification(false)}
            style={{
              position: 'fixed',
              top: 0, left: 0,
              width: '100vw', height: '100vh',
              zIndex: 150,
              // 📌 這是一個透明的全螢幕遮罩
              // 點擊通知視窗以外的地方時，會觸發這個遮罩的 onClick 把視窗關掉
            }}
          />
        )}

      </div>
    </nav>
  );
}

export default Navbar;