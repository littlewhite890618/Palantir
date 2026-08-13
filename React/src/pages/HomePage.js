import React, { useState, useEffect, useRef } from 'react';
import { useNavigationType } from 'react-router-dom';
import { getAllSubsidy } from '../services/subsidyService';
import { getFavoriteIds, toggleFavorite } from '../services/favoritesService';
import MultiSelectDropdown from '../components/MultiSelectDropdown';
import SubsidyCard from '../components/SubsidyCard';

//分頁每頁顯示的筆數，固定 20 筆，方便使用者快速瀏覽
const ITEMS_PER_PAGE = 20;

//
function getPageNumbers(currentPage, totalPages) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  if (currentPage <= 4) {
    return [1, 2, 3, 4, 5, '...', totalPages];
  }
  if (currentPage >= totalPages - 3) {
    return [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }
  return [1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages];
}

// 金額分類的範圍，依據需求設計成七個區間，方便使用者快速篩選
const AMOUNT_BUCKETS = ['100萬以下', '100-500萬', '500-1000萬', '1000-3000萬', '3000萬以上', '一億以上', '依比例補助'];

function getAmountBucket(amount) {
  if (!amount) return null;
  if (amount.includes('%')) return '依比例補助';
  // 特例：「一億」是字串（不是純數字），單獨歸到「一億以上」
  if (amount === '一億') return '一億以上';
  const num = Number(amount);
  if (Number.isNaN(num)) return null;
  if (num < 100) return '100萬以下';
  if (num < 500) return '100-500萬';
  if (num < 1000) return '500-1000萬';
  if (num < 3000) return '1000-3000萬';
  if (num < 10000) return '3000萬以上';
  return '一億以上'; // 純數字 ≥ 10000萬 = 1億（防未來出現這種資料）
}

// 期限分類的範圍，依據需求設計成五個區間，方便使用者快速篩選
const DEADLINE_BUCKETS = ['已截止', '30天內截止', '30-90天內截止', '90天以上（長期）', '未提供期限'];

function getDeadlineBucket(deadline) {
  if (!deadline) return '未提供期限';
  const deadlineDate = new Date(deadline);
  const today = new Date();
  const diffDays = (deadlineDate - today) / (1000 * 60 * 60 * 24);
  if (diffDays < 0) return '已截止';
  if (diffDays < 30) return '30天內截止';
  if (diffDays < 90) return '30-90天內截止';
  return '90天以上（長期）';
}

//點選詳細頁面後返回不會重製到顯示第一頁，而是顯示該計畫案的頁面，這個功能是透過 sessionStorage 來實現的。
const VIEW_KEY = 'palentir_home_view';

function loadView() {
  try {
    const raw = sessionStorage.getItem(VIEW_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function HomePage() {
  
  // 進行判斷，若使用者是從詳細頁返回首頁，則從 sessionStorage 還原狀態；若是直接進入首頁，則使用預設值。
  const navType = useNavigationType();
  const saved = useRef(navType === 'POP' ? loadView() : {}).current;

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 🎭 VIBE: 狀態設計 — 這裡在決定「這個頁面需要記住哪些事情」
  //    keyword 是使用者目前打了什麼字
  //    searchedKeyword 是「有沒有搜尋過」的關鍵訊號：null 代表還沒搜尋。
  //    allData 是一次性抓回來的完整資料庫備份，後續的一切都靠它
  //    pageLoading 讓使用者知道「我還沒準備好，等我一下」
  //    currentPage 是瀏覽/搜尋結果共用的分頁狀態
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 這六個 state 的初始值優先從 sessionStorage 還原（沒有就用預設），
  // 這樣從詳細頁按返回時，篩選/搜尋/頁碼都會回到離開前的樣子。
  const [keyword, setKeyword] = useState(saved.keyword ?? '');
  const [searchedKeyword, setSearchedKeyword] = useState(saved.searchedKeyword ?? null);
  const [allData, setAllData] = useState([]);
  const [pageLoading, setPageLoading] = useState(true);
  const [selectedAgencies, setSelectedAgencies] = useState(saved.selectedAgencies ?? []);
  const [selectedAmountRanges, setSelectedAmountRanges] = useState(saved.selectedAmountRanges ?? []);
  const [selectedDeadlineRanges, setSelectedDeadlineRanges] = useState(saved.selectedDeadlineRanges ?? []);
  const [favoriteIds, setFavoriteIds] = useState(() => getFavoriteIds());
  const [currentPage, setCurrentPage] = useState(saved.currentPage ?? 1);

  //收藏切換收藏狀態並更新畫面
  const handleToggleFavorite = (id) => setFavoriteIds(toggleFavorite(id));

  //先抓所有的資料
  useEffect(() => {
    getAllSubsidy()
      .then(data => {
        setAllData(data);
        setPageLoading(false);
      })
      .catch(err => {
        console.error('載入資料失敗', err);
        setPageLoading(false); // 就算失敗也要讓頁面正常顯示，不能永遠轉圈圈
      });
  }, []);

  // 計算各機關的補助案數量，並依照數量排序，方便使用者快速篩選
  const agencyCounts = allData.reduce((counts, item) => {
    if (item.category) counts[item.category] = (counts[item.category] || 0) + 1;
    return counts;
  }, {});
  const agencyOptions = Object.keys(agencyCounts).sort((a, b) => agencyCounts[b] - agencyCounts[a]);

  //三個篩選維度彼此 AND；同一維度內多選彼此 OR。空陣列代表「這個維度不篩選」，不是「篩掉所有東西」。
  const matchesFilters = (item) => {
    const agencyOk = selectedAgencies.length === 0 || selectedAgencies.includes(item.category);
    const amountOk = selectedAmountRanges.length === 0 || selectedAmountRanges.includes(getAmountBucket(item.amount));
    const deadlineOk = selectedDeadlineRanges.length === 0 || selectedDeadlineRanges.includes(getDeadlineBucket(item.deadline));
    return agencyOk && amountOk && deadlineOk;
  };
  //篩選後的清單，這個清單會再依照「有沒有搜尋」的狀態，決定要不要再套一次關鍵字搜尋。
  const filteredData = allData.filter(matchesFilters);

  //搜尋邏輯
  const handleSearch = () => {
    if (!keyword.trim()) return; // 防止使用者按下空白搜尋，浪費時間
    setSearchedKeyword(keyword);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  //決定要顯示哪份清單：若有搜尋關鍵字，就用搜尋結果；若沒有，就用篩選後的清單。
  const searchResults = searchedKeyword !== null
    ? filteredData.filter(item => item.title?.includes(searchedKeyword))
    : null;
  const isShowingSearchResults = searchedKeyword !== null;
  const baseList = isShowingSearchResults ? searchResults : filteredData;

  const totalPages = Math.ceil(baseList.length / ITEMS_PER_PAGE);
  const currentItems = baseList.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );
  const pageNumbers = getPageNumbers(currentPage, totalPages);

  //篩選或搜尋條件一有變動，就把頁碼重置回第一頁，避免使用者看到空白頁面。
  const isFirstRun = useRef(true);
  useEffect(() => {
    if (isFirstRun.current) {
      isFirstRun.current = false;   // 首次掛載：只把旗標關掉，不動頁碼（保住還原值）
      return;
    }
    setCurrentPage(1);
  }, [selectedAgencies, selectedAmountRanges, selectedDeadlineRanges, searchedKeyword]);

  //把目前的篩選/搜尋/頁碼狀態存到 sessionStorage，方便使用者從詳細頁返回時還原。
  useEffect(() => {
    const view = {
      keyword, searchedKeyword,
      selectedAgencies, selectedAmountRanges, selectedDeadlineRanges,
      currentPage,
    };
    try {
      sessionStorage.setItem(VIEW_KEY, JSON.stringify(view));
    } catch {
      // sessionStorage 滿了或被禁用——還原只是體驗優化，失敗就算了，不影響功能
    }
  }, [keyword, searchedKeyword, selectedAgencies, selectedAmountRanges, selectedDeadlineRanges, currentPage]);

  const pageButtonStyle = (isActive, isDisabled) => ({
    minWidth: '36px',
    height: '36px',
    padding: '0 8px',
    border: isActive ? '2px solid #1a73e8' : '1.5px solid #ddd',
    borderRadius: '8px',
    background: isActive ? '#1a73e8' : 'white',
    color: isActive ? 'white' : isDisabled ? '#ccc' : '#333',
    cursor: isDisabled ? 'not-allowed' : 'pointer',
    fontSize: '14px',
    fontWeight: isActive ? '600' : '400',
    transition: 'all 0.2s',
  });

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // ⏳ VIBE: 資料還沒到之前，先給個「我在努力中」的訊號
  //    避免使用者看到空白頁面以為網站壞了，提前離開。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  if (pageLoading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', marginTop: '100px', color: '#888' }}>
        載入中...
      </div>
    );
  }

  return (
    <div className="page-container">

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          💬 VIBE: 標題是情緒的起點
          「來找尋適合你的補助案」不是標題，是一句邀請。
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <h2 style={{
        fontSize: '24px',
        fontWeight: '700',
        color: '#333',
        marginTop: '100px',
        marginBottom: '20px',
        textAlign: 'center',
      }}>
        來找尋適合你的補助案！
      </h2>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          🔍 VIBE: 搜尋框是整個流程的入口，設計上刻意保持輕量
          ✕ 按鈕只有輸入內容時才出現，不打擾、不佔位，需要時它就在那裡。
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <div className="card" style={{ marginBottom: '32px' }}>
        <div style={{ position: 'relative' }}>
          <div style={{ display: 'flex', alignItems: 'center', overflow: 'hidden', transition: 'all 0.2s', background: 'white' }}>
            <button
              onClick={handleSearch}
              style={{
                padding: '14px 16px', border: 'none', background: 'transparent',
                cursor: 'pointer', color: keyword ? '#1a73e8' : '#aaa',
                fontSize: '18px', transition: 'color 0.2s',
              }}
            >
              🔍
            </button>
            <input
              type="text"
              placeholder="輸入補助案關鍵字，例如：數位轉型、農業、綠能..."
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyDown={handleKeyDown}
              style={{ flex: 1, padding: '14px 8px', border: 'none', fontSize: '15px', outline: 'none', background: 'transparent' }}
            />
            {keyword && (
              <button
                onClick={() => { setSearchedKeyword(null); setKeyword(''); }} // 清除時同步重置搜尋狀態，回到瀏覽模式
                style={{ padding: '14px 16px', border: 'none', background: 'transparent', cursor: 'pointer', color: '#aaa', fontSize: '18px' }}
              >
                ✕
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          🔽 VIBE: 三個篩選下拉——機關/金額/期限，彼此 AND，維度內多選 OR。
          勾選會立即反映在下方清單，不用重新按搜尋。
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '24px' }}>
        <MultiSelectDropdown
          label="機關"
          options={agencyOptions}
          selectedValues={selectedAgencies}
          onChange={setSelectedAgencies}
        />
        <MultiSelectDropdown
          label="金額"
          options={AMOUNT_BUCKETS}
          selectedValues={selectedAmountRanges}
          onChange={setSelectedAmountRanges}
        />
        <MultiSelectDropdown
          label="期限"
          options={DEADLINE_BUCKETS}
          selectedValues={selectedDeadlineRanges}
          onChange={setSelectedDeadlineRanges}
        />
      </div>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          📊 VIBE: 「共 N 筆，第 X / Y 頁」是使用者的方位感
          瀏覽模式跟搜尋模式共用同一套分頁，只是文字描述不同。
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <p style={{ color: '#888', marginBottom: '16px', fontSize: '14px' }}>
        {isShowingSearchResults
          ? `搜尋結果：「${searchedKeyword}」共 ${baseList.length} 筆，第 ${currentPage} / ${totalPages} 頁`
          : `共 ${baseList.length} 筆補助案，第 ${currentPage} / ${totalPages} 頁`}
      </p>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          📋 VIBE: 補助案卡片 — 讓資訊密度剛剛好
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {currentItems.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', color: '#888' }}>
          {isShowingSearchResults ? '查無相關補助案，請嘗試其他關鍵字' : '目前沒有補助案資料'}
        </div>
      ) : (
        currentItems.map((item) => (
          <SubsidyCard
            key={item.id}
            item={item}
            isFavorited={favoriteIds.includes(item.id)}
            onToggleFavorite={handleToggleFavorite}
          />
        ))
      )}

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          🔢 VIBE: 分頁列只有「超過一頁」才出現
          ◀ / ▶ 箭頭在邊界時自動 disabled，防止使用者翻到不存在的頁面。
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {totalPages > 1 && (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '8px',
          marginTop: '32px',
          marginBottom: '40px',
        }}>
          <button
            onClick={() => setCurrentPage(p => p - 1)}
            disabled={currentPage === 1}
            style={pageButtonStyle(false, currentPage === 1)}
          >
            ◀
          </button>

          {pageNumbers.map((page, index) => (
            <button
              key={index}
              onClick={() => page !== '...' && setCurrentPage(page)}
              disabled={page === '...'}
              style={{
                ...pageButtonStyle(page === currentPage, page === '...'),
                cursor: page === '...' ? 'default' : 'pointer',
              }}
            >
              {page}
            </button>
          ))}

          <button
            onClick={() => setCurrentPage(p => p + 1)}
            disabled={currentPage === totalPages}
            style={pageButtonStyle(false, currentPage === totalPages)}
          >
            ▶
          </button>
        </div>
      )}
    </div>
  );
}

export default HomePage;
