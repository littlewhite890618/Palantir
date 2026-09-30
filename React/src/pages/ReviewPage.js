import React, { useState, useEffect, useMemo } from 'react';
import { FileText, Wallet, CalendarClock, Clock, Check, X, AlertTriangle, Search, ChevronRight } from 'lucide-react';
import { LOCAL_API_URL } from '../services/subsidyService';
import { fetchPending, fetchRunSummary, approvePending, rejectPending } from '../services/reviewService';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 審核頁只在本機開發模式存在——管線抓到的新案先進待審表 subsidies_pending，
//    這裡逐筆判斷「要不要放進正式表」。正式站（GitHub Pages）是靜態站、沒有後端，
//    也不會設 LOCAL_API_URL，所以這一頁在線上根本不會被註冊（App.js）。
//    這裡再判斷一次，是為了「直接輸入 /admin 網址」也擋得住。
//
//    疑似舊案：後端用（機關, 網址）比對不到時，會再跟同機關同網域的舊案比標題相似度，
//    ≥0.85 就標出來。它只是提示，不是結論——並排比對就是要讓人一眼看出是不是同一筆。
//
//    2026-09-30 改版：清單只顯示待審核（status=pending），通過/退回後那筆照舊立即從
//    清單消失——這點刻意沒有照參考圖做成「顯示全部歷史含已通過/已拒絕」，因為那是
//    行為改變，使用者確認過維持現狀。畫面上狀態徽章固定顯示「待審核」也是因此。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// 卡片左側的彩色圖示：用申請機關字串算出固定顏色，同機關的案子顏色一致，
// 純粹視覺分類、沒有業務意義。跟 dataviz 慣例一致，用飽和度適中的色票。
const ICON_COLORS = ['#1a73e8', '#7c3aed', '#059669', '#d97706', '#0891b2', '#db2777'];
function colorForCategory(category) {
  const s = category || '';
  let hash = 0;
  for (let i = 0; i < s.length; i++) hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
  return ICON_COLORS[hash % ICON_COLORS.length];
}

const labelStyle = { fontSize: '12px', color: '#9ca3af', marginBottom: '2px' };
const valueStyle = { fontSize: '14px', color: '#1a1a1a', wordBreak: 'break-all' };

// 展開後的長文欄位：空值留白（跟詳細頁一致，不硬填「無」），保留原文換行排版
function Field({ label, value }) {
  return (
    <div style={{ marginBottom: '12px' }}>
      <div style={labelStyle}>{label}</div>
      <div style={{ ...valueStyle, whiteSpace: 'pre-wrap' }}>{value || ''}</div>
    </div>
  );
}

// 並排比對的一列：左右值不同就標色，一眼看出差在哪
function CompareRow({ label, left, right }) {
  const differs = (left || '') !== (right || '');
  const cell = (v) => ({
    ...valueStyle,
    flex: 1,
    padding: '6px 8px',
    borderRadius: '6px',
    backgroundColor: differs ? '#fff7ed' : 'transparent',
    color: differs ? '#9a3412' : '#1a1a1a',
  });
  return (
    <div style={{ marginBottom: '6px' }}>
      <div style={labelStyle}>{label}</div>
      <div className="review-compare-row" style={{ display: 'flex', gap: '8px' }}>
        <div style={cell(left)}>{left || ''}</div>
        <div style={cell(right)}>{right || ''}</div>
      </div>
    </div>
  );
}

// 一筆待審案的搜尋比對範圍：標題、機關、關鍵字（含描述/資格等長文欄位）
function matchesQuery(row, q) {
  if (!q) return true;
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  const haystack = [
    row.title, row.category, row.description, row.eligibility,
    row.required_documents, row.application_method, row.contact_window,
  ].filter(Boolean).join(' ').toLowerCase();
  return haystack.includes(needle);
}

function ReviewPage() {
  const [rows, setRows] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [openId, setOpenId] = useState(null);
  const [busyId, setBusyId] = useState(null);      // 送出中的那筆，避免重複點擊
  const [toast, setToast] = useState('');          // 成功提示
  const [actionError, setActionError] = useState('');
  const [query, setQuery] = useState('');          // 搜尋標題／機關／關鍵字

  useEffect(() => {
    if (!LOCAL_API_URL) { setLoading(false); return; }
    Promise.all([fetchPending(), fetchRunSummary().catch(() => null)])
      .then(([pending, run]) => {
        setRows(pending);
        setSummary(run);
      })
      .catch((err) => setLoadError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const filteredRows = useMemo(
    () => rows.filter((r) => matchesQuery(r, query)),
    [rows, query]
  );

  // 審核成功後只把該筆從清單移除，不重抓整份——只有一個人在審，沒有並行衝突。
  const handleAction = async (row, action) => {
    if (busyId !== null) return;
    setBusyId(row.id);
    setActionError('');
    try {
      if (action === 'approve') await approvePending(row.id);
      else await rejectPending(row.id);
      setRows((prev) => prev.filter((r) => r.id !== row.id));
      setToast(`${action === 'approve' ? '已通過' : '已退回'}：${row.title}`);
      setTimeout(() => setToast(''), 4000);
    } catch (err) {
      setActionError(`${action === 'approve' ? '通過' : '退回'}失敗：${err.message}`);
    } finally {
      setBusyId(null);
    }
  };

  if (!LOCAL_API_URL) {
    return (
      <div className="page-container" style={{ textAlign: 'center', marginTop: '100px', color: '#888' }}>
        審核頁只能在本機開發模式使用。
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', marginTop: '100px', color: '#888' }}>
        載入中...
      </div>
    );
  }

  const runLine = !summary || !summary.exists
    ? '尚無執行紀錄'
    : `上次執行：${new Date(summary.summary.finished_at).toLocaleString('zh-TW')} ${summary.summary.result}`;

  return (
    <div className="page-container review-page" style={{ paddingBottom: '48px' }}>
      <div className="review-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="review-header-icon"><FileText size={18} strokeWidth={2} /></span>
          <div>
            <h2 style={{ fontSize: '20px', margin: 0, fontWeight: 700 }}>新案審核</h2>
            <span style={{ fontSize: '12px', color: '#9ca3af' }}>{runLine}</span>
          </div>
        </div>

        {/* 搜尋標題／機關／關鍵字：純前端過濾，待審筆數不多，不需要打 API */}
        <div className="review-search">
          <Search size={15} strokeWidth={2} className="review-search-icon" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜尋標題、申請機關、關鍵字..."
          />
        </div>
      </div>

      {toast && (
        <div style={{ marginTop: '12px', padding: '10px 12px', borderRadius: '8px',
                      backgroundColor: '#ecfdf5', color: '#065f46', fontSize: '14px' }}>
          {toast}
        </div>
      )}
      {(actionError || loadError) && (
        <div style={{ marginTop: '12px', padding: '10px 12px', borderRadius: '8px',
                      backgroundColor: '#fef2f2', color: '#991b1b', fontSize: '14px' }}>
          {actionError || `載入待審清單失敗：${loadError}（確認 dev_api.py 是否已啟動）`}
        </div>
      )}

      {!loadError && rows.length === 0 && (
        <div style={{ textAlign: 'center', marginTop: '64px', color: '#888' }}>
          目前沒有待審的新案。
        </div>
      )}

      {!loadError && rows.length > 0 && filteredRows.length === 0 && (
        <div style={{ textAlign: 'center', marginTop: '64px', color: '#888' }}>
          找不到符合「{query}」的待審案。
        </div>
      )}

      {filteredRows.map((row) => {
        const open = openId === row.id;
        const dup = row.suspected_dup;
        const busy = busyId === row.id;
        const iconColor = colorForCategory(row.category);
        return (
          <div key={row.id} className="review-card">
            <div className="review-card-summary">
              <span className="review-card-icon" style={{ background: `${iconColor}1a`, color: iconColor }}>
                <FileText size={18} strokeWidth={2} />
              </span>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '15px', fontWeight: 600, marginBottom: '4px' }}>
                  {row.title}
                  {dup && (
                    <span className="review-dup-badge">
                      <AlertTriangle size={12} strokeWidth={2} /> 疑似舊案 #{dup.id}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '6px' }}>
                  {row.category}
                </div>
                {/* 金額／截止日／抓到時間：各自帶小圖示，一眼掃過去就能判斷值不值得看 */}
                <div className="review-card-meta">
                  {row.amount && (
                    <span><Wallet size={13} strokeWidth={2} /> {row.amount}</span>
                  )}
                  {row.deadline && (
                    <span><CalendarClock size={13} strokeWidth={2} /> {row.deadline}</span>
                  )}
                  <span>
                    <Clock size={13} strokeWidth={2} /> 抓到於 {new Date(row.first_seen_at).toLocaleDateString('zh-TW')}
                  </span>
                </div>
              </div>

              {/* 清單只會有 pending，狀態徽章固定顯示「待審核」；之後若要看歷史紀錄
                  （已通過／已拒絕）需另外開放 spec，這裡先不做 */}
              <span className="review-status-badge review-status-pending">待審核</span>

              {/* 逐筆審核，不做批次：每次新案只有個位數，逐筆比較不會誤觸 */}
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => handleAction(row, 'approve')}
                  disabled={busy}
                  className="review-btn"
                  style={{ color: '#065f46', borderColor: '#a7f3d0', backgroundColor: '#ecfdf5' }}
                >
                  <Check size={14} strokeWidth={2} /> 通過
                </button>
                <button
                  onClick={() => handleAction(row, 'reject')}
                  disabled={busy}
                  className="review-btn"
                  style={{ color: '#991b1b', borderColor: '#fecaca', backgroundColor: '#fef2f2' }}
                >
                  <X size={14} strokeWidth={2} /> 退回
                </button>
              </div>

              <button
                className="review-detail-link"
                onClick={() => setOpenId(open ? null : row.id)}
              >
                詳情 <ChevronRight size={14} strokeWidth={2} style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }} />
              </button>
            </div>

            {open && (
              <div style={{ borderTop: '1px solid #f3f4f6', padding: '16px' }}>
                {/* 疑似舊案：新案 vs 既有案並排，不用離開頁面就能判斷是不是同一筆 */}
                {dup && (
                  <div style={{ marginBottom: '20px', padding: '12px', borderRadius: '8px', backgroundColor: '#fafafa' }}>
                    <div className="review-compare-row" style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                      <div style={{ flex: 1, fontSize: '13px', fontWeight: 600 }}>本次新案</div>
                      <div style={{ flex: 1, fontSize: '13px', fontWeight: 600 }}>資料庫既有案 #{dup.id}</div>
                    </div>
                    <CompareRow label="標題" left={row.title} right={dup.title} />
                    <CompareRow label="申請機關" left={row.category} right={dup.category} />
                    <CompareRow label="補助金額" left={row.amount} right={dup.amount} />
                    <CompareRow label="申請截止日期" left={row.deadline} right={dup.deadline} />
                    <CompareRow label="連結" left={row.source_url} right={dup.source_url} />
                  </div>
                )}

                <Field label="描述" value={row.description} />
                <Field label="申請資格" value={row.eligibility} />
                <Field label="應備資料" value={row.required_documents} />
                <Field label="申請方式" value={row.application_method} />
                <Field label="諮詢窗口" value={row.contact_window} />
                <div style={labelStyle}>連結</div>
                <a href={row.source_url} target="_blank" rel="noreferrer"
                   style={{ ...valueStyle, color: '#1a73e8' }}>
                  {row.source_url}
                </a>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default ReviewPage;
