import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
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
      <div className="page-container" style={{ paddingTop: '26px', paddingBottom: '70px' }}><div className="state-block">載入中…</div></div>
    );
  }

  return (
    <div className="page-container" style={{ paddingTop: '26px', paddingBottom: '70px' }}>

      {/* 返回按鈕（比照詳細頁，回到上一頁） */}
      <button onClick={() => navigate(-1)} className="btn-quiet">
        <ChevronLeft size={15} strokeWidth={2} /> 返回
      </button>

      <div className="page-head">
        <h2>我的收藏</h2>
        <p className="page-head-note">
          {favoritedItems.length > 0
            ? <>已收藏 <span className="num" style={{ fontWeight: 700, color: 'var(--ink)' }}>{favoritedItems.length}</span> 件</>
            : '收藏的補助案只存在這台電腦，換裝置看不到'}
        </p>
      </div>

      {favoritedItems.length === 0 ? (
        <div className="state-block">
          <strong>還沒有收藏任何補助案</strong>
          在搜尋結果或補助案詳細頁按下愛心，就會出現在這裡。
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
