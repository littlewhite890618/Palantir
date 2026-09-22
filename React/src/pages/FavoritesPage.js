import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Heart } from 'lucide-react';
import { getAllSubsidy } from '../services/subsidyService';
import { getFavoriteIds, toggleFavorite } from '../services/favoritesService';
import SubsidyCard from '../components/SubsidyCard';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 收藏頁沿用「一次抓全部資料，前端過濾」的既有模式，
//    跟 HomePage 一致，不用另外開一支只拿收藏資料的 API。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function FavoritesPage() {
  const navigate = useNavigate();
  const [allData, setAllData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [favoriteIds, setFavoriteIds] = useState(() => getFavoriteIds());
  //一次抓全部資料，前端過濾出收藏的補助案
  useEffect(() => {
    getAllSubsidy()
      .then(data => {
        setAllData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('載入資料失敗', err);
        setLoading(false);
      });
  }, []);
  //收到收藏的計畫id後，切換收藏狀態並更新畫面
  const handleToggleFavorite = (id) => setFavoriteIds(toggleFavorite(id));
  
  //篩選出收藏的補助案
  const favoritedItems = allData.filter((item) => favoriteIds.includes(item.id));

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', marginTop: '100px', color: '#888' }}>
        載入中...
      </div>
    );
  }

  return (
    <div className="page-container">

      {/* 返回按鈕（比照詳細頁，回到上一頁） */}
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

      <h2 style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
        fontSize: '22px',
        fontWeight: '700',
        color: '#1a1a1a',
        marginTop: '16px',
        marginBottom: '20px',
        textAlign: 'center',
      }}>
        <Heart size={19} strokeWidth={1.75} color="#1a73e8" fill="#1a73e8" /> 我的收藏
      </h2>

      {favoritedItems.length === 0 ? (
        <div style={{ textAlign: 'center', color: '#9ca3af', padding: '60px 0' }}>
          還沒有收藏任何補助案
        </div>
      ) : (
        favoritedItems.map((item) => (
          <SubsidyCard
            key={item.id}
            item={item}
            isFavorited={true}
            onToggleFavorite={handleToggleFavorite}
          />
        ))
      )}
    </div>
  );
}

export default FavoritesPage;
