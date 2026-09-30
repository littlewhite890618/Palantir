import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, AlertCircle } from 'lucide-react';
import { LOCAL_API_URL } from '../services/subsidyService';
import { fetchApproved, filterLatestBatch } from '../services/notificationService';
import { getFavoriteIds, toggleFavorite } from '../services/favoritesService';
import SubsidyCard from '../components/SubsidyCard';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 通知鈴鐺點進來的目的地——列出「剛才通知的那批」審核通過新案。
//
//    為什麼不是用「未讀」去算：點鈴鐺的當下 markSeen() 就把已讀時間推到「現在」了，
//    等畫面跳到這裡，未讀一定是 0 筆、清單會空白。所以改用「前一次已讀時間」當分界
//    （見 notificationService.filterLatestBatch）。好處是重新整理不會變空白、
//    直接輸入網址進來也看得到最近一批，而不是一片空。
//
//    卡片直接重用搜尋頁的 SubsidyCard：外觀、點進詳細頁、收藏行為全部一致，
//    不另外維護一套。但要注意 SubsidyCard 是拿 item.id 去跳頁和記收藏的，
//    所以傳進去前必須把 id 換成正式表的 subsidy_id（待審表的 id 是另一組編號）。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// 正式表那筆被刪掉時（subsidy_id 為 null）用的簡化卡片：內容照顯示，但不可點、不能收藏，
// 免得跳到不存在的詳細頁。實務上只有手動刪過正式表資料才會遇到。
function OrphanCard({ item }) {
  return (
    <div className="result-item" style={{ cursor: 'default', opacity: 0.75 }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#1a1a1a', marginBottom: '4px' }}>
          {item.title}
        </h4>
        <p style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '8px' }}>{item.category}</p>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: '4px',
          fontSize: '12px', color: '#92400e', background: '#fffbeb',
          borderRadius: '999px', padding: '3px 10px',
        }}>
          <AlertCircle size={12} strokeWidth={2} /> 此案已不在資料庫中
        </span>
      </div>
    </div>
  );
}

function NewCasesPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [favoriteIds, setFavoriteIds] = useState(() => getFavoriteIds());

  useEffect(() => {
    if (!LOCAL_API_URL) { setLoading(false); return; }
    fetchApproved()
      .then((all) => setRows(filterLatestBatch(all)))
      .catch((err) => setLoadError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleToggleFavorite = (id) => setFavoriteIds(toggleFavorite(id));

  if (!LOCAL_API_URL) {
    return (
      <div className="page-container" style={{ textAlign: 'center', marginTop: '100px', color: '#888' }}>
        新案列表只能在本機開發模式使用。
      </div>
    );
  }

  return (
    <div className="page-container" style={{ paddingBottom: '48px' }}>
      <button
        onClick={() => navigate(-1)}
        style={{
          display: 'flex', alignItems: 'center', gap: '4px',
          border: 'none', background: 'transparent', cursor: 'pointer',
          color: '#1a73e8', fontSize: '14px', padding: '8px 0', marginTop: '24px',
        }}
      >
        <ChevronLeft size={16} strokeWidth={1.75} /> 返回
      </button>

      <h2 style={{ fontSize: '22px', margin: '8px 0 20px' }}>
        新增的補助案{!loading && !loadError && rows.length > 0 && `（${rows.length}）`}
      </h2>

      {loading && (
        <div style={{ textAlign: 'center', marginTop: '64px', color: '#888' }}>載入中...</div>
      )}

      {loadError && (
        <div style={{ marginTop: '12px', padding: '10px 12px', borderRadius: '8px',
                      backgroundColor: '#fef2f2', color: '#991b1b', fontSize: '14px' }}>
          載入新案清單失敗：{loadError}（確認 dev_api.py 是否已啟動）
        </div>
      )}

      {!loading && !loadError && rows.length === 0 && (
        <div style={{ textAlign: 'center', marginTop: '64px', color: '#888' }}>
          目前沒有新增的補助案。
        </div>
      )}

      {!loading && !loadError && rows.map((row) => (
        row.subsidy_id ? (
          // SubsidyCard 用 item.id 跳詳細頁與記收藏 → 必須換成正式表的 id
          <SubsidyCard
            key={row.id}
            item={{ ...row, id: row.subsidy_id }}
            isFavorited={favoriteIds.includes(row.subsidy_id)}
            onToggleFavorite={handleToggleFavorite}
          />
        ) : (
          <OrphanCard key={row.id} item={row} />
        )
      ))}
    </div>
  );
}

export default NewCasesPage;
