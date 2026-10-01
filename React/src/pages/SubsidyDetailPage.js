import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronLeft, Heart, ExternalLink,
  FileText, ClipboardList, Send, Paperclip, Phone,
} from 'lucide-react';
import { getAllSubsidy } from '../services/subsidyService';
import { getFavoriteIds, toggleFavorite } from '../services/favoritesService';
import { formatAmount } from '../utils/format';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 詳細頁就是把卷宗攤開。內容分節、每節之間用實線收邊，
//    正文行距放寬、限制在 70 字元內——這裡是真的要「讀」的地方，
//    跟列表頁的掃描節奏不同。標題用宋體，正文用黑體。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function Section({ icon: Icon, title, content }) {
  if (!content) return null; // 空值直接不渲染這個區塊，避免一堆空標題
  return (
    <section style={{ marginBottom: '30px' }}>
      <h3 style={{
        display: 'flex', alignItems: 'center', gap: '8px',
        fontSize: '16px', marginBottom: '12px', paddingBottom: '9px',
        borderBottom: '1px solid var(--rule-strong)',
      }}>
        <Icon size={16} strokeWidth={2} color="var(--seal)" /> {title}
      </h3>
      <div style={{
        whiteSpace: 'pre-wrap',   // 保留換行與縮排，長行自動折行
        lineHeight: 1.9,
        fontSize: '15px',
        color: 'var(--ink-70)',
        maxWidth: '70ch',
      }}>
        {content}
      </div>
    </section>
  );
}

// 金額與截止日：帳冊格式，等寬數字。截止日在 14 天內轉硃紅
const D_FULL = /(\d{2,4})\s*[年/.\-]\s*(\d{1,2})\s*[月/.\-]\s*(\d{1,2})/g;
function daysUntil(deadline) {
  if (!deadline) return null;
  let latest = null;
  for (const m of deadline.matchAll(D_FULL)) {
    const y = +m[1] < 1911 ? +m[1] + 1911 : +m[1];
    const t = new Date(y, +m[2] - 1, +m[3]).getTime();
    if (latest === null || t > latest) latest = t;
  }
  return latest === null ? null : Math.ceil((latest - Date.now()) / 86400000);
}

function SubsidyDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [favoriteIds, setFavoriteIds] = useState(() => getFavoriteIds());

  //在id變動時，重新抓取資料，找到對應的補助案並更新狀態
  useEffect(() => {
    getAllSubsidy()
      .then(data => {
        const found = data.find((s) => String(s.id) === id);
        setItem(found || null);
        setLoading(false);
      })
      .catch(err => {
        console.error('載入資料失敗', err);
        setLoading(false);
      });
  }, [id]);

  const isFavorited = item ? favoriteIds.includes(item.id) : false;
  const daysLeft = item ? daysUntil(item.deadline) : null;
  const handleToggleFavorite = () => setFavoriteIds(toggleFavorite(item.id));

  if (loading) {
    return (
      <div className="page-container"><div className="state-block">載入中…</div></div>
    );
  }

  // 找不到對應 id 的補助案（例如網址亂打）
  if (!item) {
    return (
      <div className="page-container">
        <div className="state-block">
          <strong>找不到這筆補助案</strong>
          這個編號不存在，可能是網址輸入錯誤，或這筆資料已被移除。
        </div>
        <button onClick={() => navigate('/')} className="btn btn-primary">回首頁重新搜尋</button>
      </div>
    );
  }

  return (
    <div className="page-container" style={{ paddingTop: '26px', paddingBottom: '70px' }}>

      {/* 返回按鈕 */}
      <button onClick={() => navigate(-1)} className="btn-quiet" style={{ marginBottom: '14px' }}>
        <ChevronLeft size={15} strokeWidth={2} /> 返回搜尋結果
      </button>

      {/* 標題區：案號在最上，像卷宗編號；機關用純文字不做成膠囊標籤 */}
      <div style={{ marginBottom: '22px' }}>
        <span className="num" style={{ fontSize: '12px', color: 'var(--ink-25)' }}>
          No.{String(item.id).padStart(4, '0')}
        </span>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', marginTop: '4px' }}>
          <div>
            <h2 style={{ fontSize: '26px', lineHeight: 1.35, marginBottom: '6px', maxWidth: '24ch' }}>
              {item.title}
            </h2>
            <p style={{ fontSize: '14px', color: 'var(--ink-45)' }}>{item.category}</p>
          </div>

          <button
            onClick={handleToggleFavorite}
            title={isFavorited ? '取消收藏' : '加入收藏'}
            className="btn"
            style={{
              flexShrink: 0, padding: '8px 14px', fontSize: '13px',
              background: isFavorited ? 'var(--seal-wash)' : 'var(--paper-raised)',
              color: isFavorited ? 'var(--seal)' : 'var(--ink-70)',
              borderColor: isFavorited ? 'var(--seal)' : 'var(--rule-strong)',
            }}
          >
            <Heart size={15} strokeWidth={1.75} fill={isFavorited ? 'currentColor' : 'none'} />
            {isFavorited ? '已收藏' : '收藏'}
          </button>
        </div>

        {item.source_url && (
          <a
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '13px', marginTop: '12px' }}
          >
            <ExternalLink size={13} strokeWidth={1.75} /> 開啟原始公告檔案
          </a>
        )}
      </div>

      {/* 主要資訊：帳冊列，等寬數字。截止日 14 天內轉硃紅 */}
      <div className="ledger-row" style={{ marginBottom: '34px', borderTop: '2px solid var(--ink)', paddingTop: '14px' }}>
        <div className="ledger-cell">
          <span className="ledger-label">補助金額</span>
          <span className={`ledger-value${item.amount ? '' : ' ledger-value--none'}`} style={{ fontSize: '15px' }}>
            {item.amount ? formatAmount(item.amount) : '未提供'}
          </span>
        </div>
        <div className="ledger-cell">
          <span className="ledger-label">申請截止</span>
          <span
            className={`ledger-value${daysLeft !== null && daysLeft >= 0 && daysLeft <= 14 ? ' ledger-value--urgent' : ''}${item.deadline ? '' : ' ledger-value--none'}`}
            style={{ fontSize: '15px' }}
          >
            {item.deadline || '未提供'}
            {daysLeft !== null && daysLeft >= 0 && daysLeft <= 14 && `（剩 ${daysLeft} 天）`}
          </span>
        </div>
      </div>

      {/* 內容區塊：計畫內容 → 申請資格 → 申請方式 → 應備資料 → 諮詢窗口 */}
      <Section icon={FileText} title="計畫內容" content={item.description} />
      <Section icon={ClipboardList} title="申請資格" content={item.eligibility} />
      <Section icon={Send} title="申請方式" content={item.application_method} />
      <Section icon={Paperclip} title="應備資料" content={item.required_documents} />
      <Section icon={Phone} title="諮詢窗口" content={item.contact_window} />
    </div>
  );
}

export default SubsidyDetailPage;
