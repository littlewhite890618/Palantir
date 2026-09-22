import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Heart, Calendar, Wallet, Download, ChevronRight } from 'lucide-react';
import { formatAmount } from '../utils/format';

// HomePage(搜尋結果) 和 FavoritesPage 共用的補助案列表項元件
// 顯示標題、分類、描述、截止日期、金額、收藏狀態和下載按鈕

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
    //整列可點進詳細頁；收藏與下載按鈕各自 stopPropagation，不觸發跳頁
    <div className="result-item" onClick={() => navigate(`/subsidy/${item.id}`)}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
          <h4 style={{ fontSize: '16px', fontWeight: '600', color: '#1a1a1a' }}>{item.title}</h4>
        </div>
        <p style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '6px' }}>{item.category}</p>
        {item.description && (
          <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '10px', lineHeight: 1.5 }}>
            {truncateDescription(item.description)}
          </p>
        )}
        <div style={{ display: 'flex', gap: '16px', fontSize: '13px', color: '#9ca3af' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Wallet size={13} strokeWidth={1.75} /> {formatAmount(item.amount)}
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Calendar size={13} strokeWidth={1.75} /> 申請截止 {item.deadline || '未提供'}
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
        <button
          onClick={(e) => { e.stopPropagation(); onToggleFavorite(item.id); }}
          title={isFavorited ? '取消收藏' : '加入收藏'}
          style={{
            border: 'none', background: 'transparent', cursor: 'pointer',
            padding: '6px', display: 'flex', color: isFavorited ? '#1a73e8' : '#c7cbd1',
          }}
        >
          <Heart size={17} strokeWidth={1.75} fill={isFavorited ? '#1a73e8' : 'none'} />
        </button>

        {item.source_url ? (
          <a
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            title="開啟原始檔案"
            onClick={(e) => e.stopPropagation()}
            style={{ padding: '6px', display: 'flex', color: '#9ca3af' }}
          >
            <Download size={16} strokeWidth={1.75} />
          </a>
        ) : (
          <span
            title="無原始檔案連結"
            onClick={(e) => e.stopPropagation()}
            style={{ padding: '6px', display: 'flex', color: '#e5e7eb', cursor: 'not-allowed' }}
          >
            <Download size={16} strokeWidth={1.75} />
          </span>
        )}

        <ChevronRight size={17} strokeWidth={1.75} color="#c7cbd1" />
      </div>
    </div>
  );
}

export default SubsidyCard;
