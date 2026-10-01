import React, { useState, useEffect, useMemo } from 'react';
import { Check, X, Search, ChevronRight } from 'lucide-react';
import { LOCAL_API_URL } from '../services/subsidyService';
import { fetchPending, fetchRunSummary, approvePending, rejectPending } from '../services/reviewService';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 審核頁只在本機開發模式存在——管線抓到的新案先進待審表 subsidies_pending，
//    這裡逐筆判斷「要不要放進正式表」。正式站（GitHub Pages）是靜態站、沒有後端，
//    也不會設 LOCAL_API_URL，所以這一頁在線上根本不會被註冊（App.js）。
//    這裡再判斷一次，是為了「直接輸入 /admin 網址」也擋得住。
//
//    清單只顯示待審核（status=pending），通過/退回後那筆立即消失。
//
//    疑似舊案：後端用（機關, 網址）比對不到時，會再跟同機關同網域的舊案比標題相似度，
//    ≥0.85 就標出來。它只是提示，不是結論——並排比對就是要讓人一眼看出是不是同一筆。
//    不同的欄位轉硃紅，相同的維持墨色，差異自己會跳出來。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// 展開後的長文欄位：空值留白（跟詳細頁一致，不硬填「無」），保留原文換行排版
function Field({ label, value }) {
  return (
    <div className="detail-field">
      <div className="detail-label">{label}</div>
      <div className={`detail-value${value ? '' : ' detail-value--empty'}`}>
        {value || '未提供'}
      </div>
    </div>
  );
}

// 並排比對的一列：左右值不同就轉硃紅
function CompareRow({ label, left, right }) {
  const differs = (left || '') !== (right || '');
  const cls = `compare-value${differs ? ' compare-value--differs' : ''}`;
  return (
    <>
      <div className="compare-label">{label}</div>
      <div className={cls}>{left || '—'}</div>
      <div className={cls}>{right || '—'}</div>
    </>
  );
}

// 搜尋比對範圍：標題、機關、以及各長文欄位
function matchesQuery(row, q) {
  const needle = (q || '').trim().toLowerCase();
  if (!needle) return true;
  return [
    row.title, row.category, row.description, row.eligibility,
    row.required_documents, row.application_method, row.contact_window,
  ].filter(Boolean).join(' ').toLowerCase().includes(needle);
}

function ReviewPage() {
  const [rows, setRows] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [openId, setOpenId] = useState(null);
  const [busyId, setBusyId] = useState(null);      // 送出中的那筆，避免重複點擊
  const [toast, setToast] = useState('');
  const [actionError, setActionError] = useState('');
  const [query, setQuery] = useState('');

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

  const filteredRows = useMemo(() => rows.filter((r) => matchesQuery(r, query)), [rows, query]);

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
    return <div className="page-container"><div className="state-block">審核頁只能在本機開發模式使用。</div></div>;
  }

  if (loading) {
    return <div className="page-container"><div className="state-block">載入中…</div></div>;
  }

  const runLine = !summary || !summary.exists
    ? '尚無管線執行紀錄'
    : `上次執行 ${new Date(summary.summary.finished_at).toLocaleString('zh-TW')}　${summary.summary.result}`;

  return (
    <div className="page-container review-page" style={{ paddingBottom: '64px' }}>
      <div className="page-head" style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2>新案審核</h2>
          <p className="page-head-note">
            待審 <span className="num" style={{ fontWeight: 700, color: 'var(--ink)' }}>{rows.length}</span> 件
            <span style={{ paddingLeft: '12px', marginLeft: '12px', borderLeft: '1px solid var(--rule-strong)' }}>
              {runLine}
            </span>
          </p>
        </div>

        {/* 待審筆數不多，純前端過濾就夠，不必打 API */}
        <div className="review-search">
          <Search size={15} strokeWidth={2} className="review-search-icon" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜尋標題、機關、內容"
            aria-label="搜尋待審案"
          />
        </div>
      </div>

      {toast && <div className="notice notice--ok">{toast}</div>}
      {(actionError || loadError) && (
        <div className="notice notice--bad">
          {actionError || `載入待審清單失敗：${loadError}　請確認 dev_api.py 已啟動。`}
        </div>
      )}

      {!loadError && rows.length === 0 && (
        <div className="state-block">
          <strong>目前沒有待審的新案</strong>
          管線跑完抓到資料庫沒有的補助案時，會出現在這裡等你審核。
        </div>
      )}

      {!loadError && rows.length > 0 && filteredRows.length === 0 && (
        <div className="state-block">
          <strong>沒有符合「{query}」的待審案</strong>
          清空搜尋框可以看到全部 {rows.length} 件。
        </div>
      )}

      {filteredRows.map((row) => {
        const open = openId === row.id;
        const dup = row.suspected_dup;
        const busy = busyId === row.id;
        return (
          <div
            key={row.id}
            className="dossier"
            style={{ borderLeftColor: dup ? 'var(--vermilion)' : 'var(--seal)' }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '18px', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: '240px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '3px' }}>
                  <span className="stamp stamp--pending">待審核</span>
                  {dup && <span className="stamp stamp--alert">疑似舊案 No.{String(dup.id).padStart(4, '0')}</span>}
                </div>

                <h3 className="dossier-title" style={{ paddingRight: 0 }}>{row.title}</h3>
                <p className="dossier-agency">{row.category}</p>

                <div className="ledger-row">
                  <div className="ledger-cell">
                    <span className="ledger-label">補助金額</span>
                    <span className={`ledger-value${row.amount ? '' : ' ledger-value--none'}`}>
                      {row.amount || '未提供'}
                    </span>
                  </div>
                  <div className="ledger-cell">
                    <span className="ledger-label">申請截止</span>
                    <span className={`ledger-value${row.deadline ? '' : ' ledger-value--none'}`}>
                      {row.deadline || '未提供'}
                    </span>
                  </div>
                  <div className="ledger-cell">
                    <span className="ledger-label">抓取日期</span>
                    <span className="ledger-value">
                      {new Date(row.first_seen_at).toLocaleDateString('zh-TW')}
                    </span>
                  </div>
                </div>
              </div>

              {/* 逐筆審核，不做批次：每次新案只有個位數，逐筆比較不會誤觸 */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'stretch' }}>
                <div className="review-actions">
                  <button
                    onClick={() => handleAction(row, 'approve')}
                    disabled={busy}
                    className="review-btn review-btn--approve"
                  >
                    <Check size={14} strokeWidth={2.5} /> 通過
                  </button>
                  <button
                    onClick={() => handleAction(row, 'reject')}
                    disabled={busy}
                    className="review-btn review-btn--reject"
                  >
                    <X size={14} strokeWidth={2.5} /> 退回
                  </button>
                </div>

                <button className="btn-quiet" onClick={() => setOpenId(open ? null : row.id)} style={{ justifyContent: 'flex-end' }}>
                  {open ? '收合內容' : '展開內容'}
                  <ChevronRight
                    size={14}
                    strokeWidth={2}
                    style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 0.12s' }}
                  />
                </button>
              </div>
            </div>

            {open && (
              <div style={{ marginTop: '18px' }}>
                {/* 疑似舊案：新案 vs 既有案並排，不用離開頁面就能判斷是不是同一筆 */}
                {dup && (
                  <div className="compare-grid">
                    <div className="compare-head">本次新案</div>
                    <div className="compare-head">資料庫既有案 No.{String(dup.id).padStart(4, '0')}</div>
                    <CompareRow label="標題" left={row.title} right={dup.title} />
                    <CompareRow label="申請機關" left={row.category} right={dup.category} />
                    <CompareRow label="補助金額" left={row.amount} right={dup.amount} />
                    <CompareRow label="申請截止" left={row.deadline} right={dup.deadline} />
                    <CompareRow label="連結" left={row.source_url} right={dup.source_url} />
                  </div>
                )}

                <Field label="計畫內容" value={row.description} />
                <Field label="申請資格" value={row.eligibility} />
                <Field label="應備資料" value={row.required_documents} />
                <Field label="申請方式" value={row.application_method} />
                <Field label="諮詢窗口" value={row.contact_window} />

                <div className="detail-field">
                  <div className="detail-label">原始檔案連結</div>
                  <a href={row.source_url} target="_blank" rel="noreferrer" style={{ fontSize: '14px', wordBreak: 'break-all' }}>
                    {row.source_url}
                  </a>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default ReviewPage;
