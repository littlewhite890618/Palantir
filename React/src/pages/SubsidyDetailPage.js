import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getAllSubsidy } from '../services/subsidyService';
import { formatAmount } from '../utils/format';



const documentTextStyle = {
  whiteSpace: 'pre-wrap',   // 保留換行與縮排，長行自動折行
  lineHeight: 1.9,          // 寬鬆行距，像在讀文件
  fontSize: '15px',
  color: '#333',
};

function DocumentSection({ icon, title, content }) {
  return (
    <div className="card" style={{ marginBottom: '24px' }}>
      <h3 style={{
        fontSize: '18px',
        fontWeight: '700',
        color: '#1a73e8',
        marginBottom: '16px',
        paddingBottom: '12px',
        borderBottom: '1px solid #eee',
      }}>
        {icon} {title}
      </h3>
      {/* 空值直接留白（不顯示佔位文字） */}
      <div style={documentTextStyle}>{content || ''}</div>
    </div>
  );
}

function SubsidyDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
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

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', marginTop: '100px', color: '#888' }}>
        載入中...
      </div>
    );
  }

  // 找不到對應 id 的補助案（例如網址亂打）
  if (!item) {
    return (
      <div className="page-container" style={{ textAlign: 'center', marginTop: '100px' }}>
        <p style={{ color: '#888', marginBottom: '20px' }}>找不到這筆補助案</p>
        <button
          onClick={() => navigate('/')}
          className="btn btn-primary"
        >
          回首頁
        </button>
      </div>
    );
  }

  return (
    <div className="page-container" style={{ marginTop: '32px', maxWidth: '860px' }}>

      {/* 返回按鈕 */}
      <button
        onClick={() => navigate(-1)}
        style={{
          border: 'none', background: 'transparent', cursor: 'pointer',
          color: '#1a73e8', fontSize: '15px', padding: '8px 0', marginBottom: '8px',
        }}
      >
        ← 返回
      </button>

      {/* 標題區 */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
          <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#333' }}>{item.title}</h2>
          <span className="tag" style={{ flexShrink: 0 }}>{item.category}</span>
        </div>
        <div style={{ display: 'flex', gap: '16px', marginTop: '12px', fontSize: '14px', color: '#888' }}>
          <span>📅 補助期限：{item.deadline}</span>
          <span>💰 {formatAmount(item.amount)}</span>
        </div>
      </div>

      {/* 上半部：申請資格 */}
      <DocumentSection icon="📋" title="申請資格" content={item.eligibility} />

      {/* 下半部：應備資料 */}
      <DocumentSection icon="📎" title="應備資料" content={item.required_documents} />

      {/* 申請方式 */}
      <DocumentSection icon="📝" title="申請方式" content={item.application_method} />

      {/* 諮詢窗口 */}
      <DocumentSection icon="📞" title="諮詢窗口" content={item.contact_window} />
    </div>
  );
}

export default SubsidyDetailPage;
