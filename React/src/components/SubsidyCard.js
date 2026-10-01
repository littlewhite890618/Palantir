import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Heart, Download } from 'lucide-react';
import { formatAmount } from '../utils/format';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 搜尋結果 / 收藏 / 新案列表共用的補助案卡片。
//
// 🧠 VIBE: 這是一份「卷宗」，不是一張 SaaS 卡片——方正邊界、靠左一條官印藍的墨條、
//    右上角是案號戳記。金額與截止日走帳冊列（等寬數字），因為這兩個值是要上下
//    比對的結構化資料：掃一整頁時，對齊的數字比對齊的句子有用得多。
//
//    截止日在 14 天內會轉成硃紅並標「即將截止」——硃紅整站只用在這裡，
//    所以它一出現就有意義，不會被當成裝飾色略過。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const MAX_DESC_LENGTH = 100;
function truncateDescription(desc) {
  if (!desc) return '';
  return desc.length > MAX_DESC_LENGTH ? `${desc.slice(0, MAX_DESC_LENGTH)}…` : desc;
}

// 民國年／中文日期都解析得動（跟 SearchResultsPage 的期限篩選同一套規則）。
// 回傳距今天數；解析不出來回 null。
const D_FULL = /(\d{2,4})\s*[年/.\-]\s*(\d{1,2})\s*[月/.\-]\s*(\d{1,2})/g;
function daysUntil(deadline) {
  if (!deadline) return null;
  let latest = null;
  for (const m of deadline.matchAll(D_FULL)) {
    const y = +m[1] < 1911 ? +m[1] + 1911 : +m[1];
    const t = new Date(y, +m[2] - 1, +m[3]).getTime();
    if (latest === null || t > latest) latest = t;
  }
  if (latest === null) return null;
  return Math.ceil((latest - Date.now()) / 86400000);
}

function SubsidyCard({ item, isFavorited, onToggleFavorite }) {
  const navigate = useNavigate();
  const left = daysUntil(item.deadline);
  const urgent = left !== null && left >= 0 && left <= 14;

  return (
    <div className="dossier dossier--link" onClick={() => navigate(`/subsidy/${item.id}`)}>
      {/* 案號戳記：資料庫 id，也是詳細頁的網址，對得起來時查起來方便 */}
      <span className="dossier-ref">No.{String(item.id).padStart(4, '0')}</span>

      <h3 className="dossier-title">{item.title}</h3>
      <p className="dossier-agency">{item.category}</p>

      {item.description && (
        <p className="dossier-excerpt">{truncateDescription(item.description)}</p>
      )}

      <div className="ledger-row">
        <div className="ledger-cell">
          <span className="ledger-label">補助金額</span>
          <span className={`ledger-value${item.amount ? '' : ' ledger-value--none'}`}>
            {item.amount ? formatAmount(item.amount) : '未提供'}
          </span>
        </div>

        <div className="ledger-cell">
          <span className="ledger-label">申請截止</span>
          <span className={`ledger-value${urgent ? ' ledger-value--urgent' : ''}${item.deadline ? '' : ' ledger-value--none'}`}>
            {item.deadline || '未提供'}
            {urgent && `（剩 ${left} 天）`}
          </span>
        </div>

        <div className="ledger-cell" style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '2px' }}>
          <button
            onClick={(e) => { e.stopPropagation(); onToggleFavorite(item.id); }}
            title={isFavorited ? '取消收藏' : '加入收藏'}
            style={{
              border: 'none', background: 'transparent', cursor: 'pointer',
              padding: '4px 6px', display: 'flex',
              color: isFavorited ? 'var(--seal)' : 'var(--ink-25)',
            }}
          >
            <Heart size={16} strokeWidth={1.75} fill={isFavorited ? 'currentColor' : 'none'} />
          </button>

          {item.source_url && (
            <a
              href={item.source_url}
              target="_blank"
              rel="noopener noreferrer"
              title="開啟原始須知檔案"
              onClick={(e) => e.stopPropagation()}
              style={{ padding: '4px 6px', display: 'flex', color: 'var(--ink-25)' }}
            >
              <Download size={16} strokeWidth={1.75} />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

export default SubsidyCard;
