import React from 'react';
import { useNavigate } from 'react-router-dom';
import { formatAmount } from '../utils/format';

// HomePage 和 FavoritesPage 共用的補助案卡片元件，顯示標題、分類、描述、截止日期、金額、收藏狀態和下載按鈕

//卡片是快速掃描用的，description 太長會撐爆版面、稀釋資訊密度。
// 限制 100 字內、超過補「…」，完整內容留給之後的詳細頁呈現。

const MAX_DESC_LENGTH = 100;
function truncateDescription(desc) {
  if (!desc) return '';
  return desc.length > MAX_DESC_LENGTH ? `${desc.slice(0, MAX_DESC_LENGTH)}…` : desc;
}

//Props: item（補助案物件）、isFavorited（是否已收藏）、onToggleFavorite（切換收藏狀態的回呼函式）
function SubsidyCard({ item, isFavorited, onToggleFavorite }) {
  const navigate = useNavigate();
  return (
    //整張卡片可點進詳細頁；愛心與下載按鈕各自 stopPropagation，不觸發跳頁
    <div className="card" onClick={() => navigate(`/subsidy/${item.id}`)} style={{ cursor: 'pointer' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <h4 style={{ fontSize: '18px', marginBottom: '8px' }}>{item.title}</h4>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <span className="tag">{item.category}</span>
          <button
            onClick={(e) => { e.stopPropagation(); onToggleFavorite(item.id); }}
            title={isFavorited ? '取消收藏' : '加入收藏'}
            style={{
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: '18px',
              padding: '0',
              lineHeight: 1,
            }}
          >
            {isFavorited ? '❤️' : '🤍'}
          </button>
        </div>
      </div>
      <p style={{ color: '#666', marginBottom: '12px', fontSize: '14px' }}>{truncateDescription(item.description)}</p>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '14px', color: '#888' }}>
          <span>📅 補助期限：{item.deadline}</span>
          <span>💰 {formatAmount(item.amount)}</span>
        </div>
       //下載按鈕，若有 source_url 則可點擊，否則顯示灰色不可點
        {item.source_url ? (
          <a
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            title="開啟原始檔案"
            onClick={(e) => e.stopPropagation()}
            style={{ fontSize: '18px', color: '#1a73e8', padding: '0', textDecoration: 'none' }}
          >
            ⬇️
          </a>
        ) : (
          <span
            title="無原始檔案連結"
            onClick={(e) => e.stopPropagation()}
            style={{ fontSize: '18px', color: '#ccc', cursor: 'not-allowed' }}
          >
            ⬇️
          </span>
        )}
      </div>
    </div>
  );
}

export default SubsidyCard;
