import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Heart, LogOut, Bell, CalendarDays } from 'lucide-react';
import { lock, getExportedAt, LOCAL_API_URL } from '../services/subsidyService';
import { fetchApproved, countUnread, markSeen } from '../services/notificationService';


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 通知鈴鐺——管理員在 /admin 審核通過的案子會在這裡顯示未讀數。
//    只在取得到資料來源時顯示（目前等同本機開發模式）。這裡刻意「不」用
//    NODE_ENV 把程式碼排除在正式產物外：鈴鐺本來就規劃要上線給一般使用者，
//    只是正式站還缺 reviewed_at 這個判斷依據。現在排除、之後上線再加回來，
//    等於白做兩次。管理台 /admin 是純內部功能才需要整段排除，兩者不同。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function NotificationBell() {
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    fetchApproved()
      .then((rows) => setUnread(countUnread(rows)))
      // 取不到就當作沒有通知，不要在搜尋器上跳錯誤打擾使用者（通知不是核心功能）
      .catch(() => setUnread(0));
  }, []);

  // 點 popover 以外的地方就關閉
  useEffect(() => {
    if (!open) return undefined;
    const onDocClick = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  // 徽章一點開就歸零，但 popover 內文要顯示「這次點開時有幾筆」，
  // 所以在歸零「之前」先把數字留在 shownCount，不能等 effect 再去讀 unread（那時已是 0）。
  const [shownCount, setShownCount] = useState(0);

  const handleBellClick = () => {
    if (open) { setOpen(false); return; }   // 再點一次只是關閉，不重複寫入已讀時間
    setShownCount(unread);
    setOpen(true);
    if (unread > 0) {
      markSeen();
      setUnread(0);   // 已讀時間已更新，直接歸零，不必重打 API
    }
  };

  return (
    <div ref={wrapRef} style={{ position: 'relative', display: 'flex' }}>
      <button onClick={handleBellClick} className="navbar-icon-btn" title="新案通知">
        <span style={{ position: 'relative', display: 'inline-flex' }}>
          <Bell size={18} strokeWidth={1.75} />
          {unread > 0 && <span className="notif-badge">{unread > 99 ? '99+' : unread}</span>}
        </span>
        <span className="nav-icon-label">新案通知</span>
      </button>

      {open && (
        <div className="notif-popover">
          {shownCount > 0 ? (
            <button
              className="notif-popover-link"
              onClick={() => { setOpen(false); navigate('/new-cases'); }}
            >
              新增了 {shownCount} 筆補助案
            </button>
          ) : (
            <div className="notif-popover-empty">目前沒有新增的補助案</div>
          )}
        </div>
      )}
    </div>
  );
}

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
    <nav className="navbar">

      {/* 左側：抬頭。思源宋體加粗，像卷宗封面上的機關名 */}
      <Link to="/" className="wordmark">Palantir</Link>

      {/* 右側：資料更新時間（極低存在感）+ 收藏 + 登出。
          窄螢幕（<480px）時文字標籤自動隱藏，只留 icon（見 App.css）。 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
        {exportedAt && (
          <span className="navbar-exported">
            資料更新 {new Date(exportedAt).toLocaleDateString('zh-TW')}
          </span>
        )}

        {/* 通知鈴鐺：只在取得到已審核資料的環境顯示（目前等同本機開發模式） */}
        {LOCAL_API_URL && <NotificationBell />}

        <Link to="/calendar" style={{ textDecoration: 'none' }}>
          <button
            className={`navbar-icon-btn${location.pathname === '/calendar' ? ' active' : ''}`}
            title="截止日行事曆"
          >
            <CalendarDays size={18} strokeWidth={1.75} />
            <span className="nav-icon-label">行事曆</span>
          </button>
        </Link>

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
