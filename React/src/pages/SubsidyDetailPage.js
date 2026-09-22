import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronLeft, Heart, Wallet, Calendar, ExternalLink,
  FileText, ClipboardList, Send, Paperclip, Phone,
} from 'lucide-react';
import { getAllSubsidy } from '../services/subsidyService';
import { getFavoriteIds, toggleFavorite } from '../services/favoritesService';
import { formatAmount } from '../utils/format';

const documentTextStyle = {
  whiteSpace: 'pre-wrap',   // 保留換行與縮排，長行自動折行
  lineHeight: 1.9,          // 寬鬆行距，像在讀文件
  fontSize: '15px',
  color: '#374151',
};

function Section({ icon: Icon, title, content }) {
  if (!content) return null; // 空值直接不渲染這個區塊，避免一堆空標題
  return (
    <div style={{ marginBottom: '28px' }}>
      <h3 style={{
        display: 'flex', alignItems: 'center', gap: '8px',
        fontSize: '16px', fontWeight: '700', color: '#1a1a1a',
        marginBottom: '12px', paddingBottom: '10px',
        borderBottom: '1px solid #eef0f2',
      }}>
        <Icon size={17} strokeWidth={1.75} color="#1a73e8" /> {title}
      </h3>
      <div style={documentTextStyle}>{content}</div>
    </div>
  );
}

function StatBox({ icon: Icon, label, value }) {
  return (
    <div style={{
      flex: 1, border: '1px solid #eef0f2', borderRadius: '10px',
      padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '6px',
    }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#9ca3af' }}>
        <Icon size={13} strokeWidth={1.75} /> {label}
      </span>
      <span style={{ fontSize: '16px', fontWeight: '700', color: '#1a1a1a' }}>{value}</span>
    </div>
  );
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
  const handleToggleFavorite = () => setFavoriteIds(toggleFavorite(item.id));

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', marginTop: '100px', color: '#9ca3af' }}>
        載入中...
      </div>
    );
  }

  // 找不到對應 id 的補助案（例如網址亂打）
  if (!item) {
    return (
      <div className="page-container" style={{ textAlign: 'center', marginTop: '100px' }}>
        <p style={{ color: '#9ca3af', marginBottom: '20px' }}>找不到這筆補助案</p>
        <button onClick={() => navigate('/')} className="btn btn-primary">回首頁</button>
      </div>
    );
  }

  return (
    <div className="page-container" style={{ marginTop: '28px', maxWidth: '720px' }}>

      {/* 返回按鈕 */}
      <button
        onClick={() => navigate(-1)}
        style={{
          display: 'flex', alignItems: 'center', gap: '4px',
          border: 'none', background: 'transparent', cursor: 'pointer',
          color: '#1a73e8', fontSize: '14px', padding: '8px 0', marginBottom: '12px',
        }}
      >
        <ChevronLeft size={16} strokeWidth={1.75} /> 返回搜尋結果
      </button>

      {/* 標題區 */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
          <div>
            <h2 style={{ fontSize: '22px', fontWeight: '700', color: '#1a1a1a', marginBottom: '6px' }}>{item.title}</h2>
            <span className="tag">{item.category}</span>
          </div>
          <button
            onClick={handleToggleFavorite}
            title={isFavorited ? '取消收藏' : '加入收藏'}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0,
              border: '1px solid #e5e7eb', background: isFavorited ? '#eaf1fd' : '#fff',
              color: isFavorited ? '#1a73e8' : '#6b7280', borderRadius: '8px',
              padding: '8px 14px', cursor: 'pointer', fontSize: '13px',
            }}
          >
            <Heart size={15} strokeWidth={1.75} fill={isFavorited ? '#1a73e8' : 'none'} /> 收藏
          </button>
        </div>

        {item.source_url && (
          <a
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '5px',
              fontSize: '13px', color: '#1a73e8', textDecoration: 'none', marginTop: '10px',
            }}
          >
            <ExternalLink size={13} strokeWidth={1.75} /> 查看原始公告
          </a>
        )}
      </div>

      {/* 主要資訊 */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '32px' }}>
        <StatBox icon={Wallet} label="最高補助" value={formatAmount(item.amount) || '未提供'} />
        <StatBox icon={Calendar} label="申請截止" value={item.deadline || '未提供'} />
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
