import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { getAllSubsidy } from '../services/subsidyService';
import { getFavoriteIds, toggleFavorite } from '../services/favoritesService';
import MultiSelectDropdown from '../components/MultiSelectDropdown';
import SubsidyCard from '../components/SubsidyCard';
import { parseLatestDeadline } from '../utils/deadline';

const ITEMS_PER_PAGE = 20;

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
  if (amount.includes('億')) return '一億以上';
  // amount 實際存的是「100萬元」「3000萬元」這種帶單位的字串，不是純數字，
  // 所以要取開頭的數字部分來判斷區間，不能直接 Number(amount)（會是 NaN）
  const match = amount.match(/^(\d+(\.\d+)?)/);
  if (!match) return null;
  const num = Number(match[1]);
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
  const deadlineDate = parseLatestDeadline(deadline);
  if (!deadlineDate) return '未提供期限'; // 抓不到任何日期（含純文字如「經費用罄為止」）也歸這裡
  const today = new Date();
  const diffDays = (deadlineDate - today) / (1000 * 60 * 60 * 24);
  if (diffDays < 0) return '已截止';
  if (diffDays < 30) return '30天內截止';
  if (diffDays < 90) return '30-90天內截止';
  return '90天以上（長期）';
}

// 篩選條件（機關/金額/期限）不放進網址，只記在 sessionStorage：
// 從詳細頁按返回時要能還原，但不需要像關鍵字一樣可分享。
const FILTER_KEY = 'palentir_search_filters';

function loadFilters() {
  try {
    const raw = sessionStorage.getItem(FILTER_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

const pageButtonStyle = (isActive, isDisabled) => ({
  minWidth: '34px',
  height: '34px',
  padding: '0 8px',
  border: `1px solid ${isActive ? 'var(--seal)' : 'var(--rule-strong)'}`,
  borderRadius: '2px',
  background: isActive ? 'var(--seal)' : 'var(--paper-raised)',
  color: isActive ? '#fff' : isDisabled ? 'var(--ink-25)' : 'var(--ink-70)',
  cursor: isDisabled ? 'not-allowed' : 'pointer',
  fontFamily: 'var(--font-mono)',
  fontSize: '13px',
  fontWeight: isActive ? 700 : 400,
});

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 搜尋結果頁 = 結果 + Filter + Sort，跟首頁（純搜尋入口）分開。
//    關鍵字放在網址 ?q=，可分享、重新整理不會跑掉；篩選邏輯完全沿用舊版
//    HomePage 的既有實作，只是重新設計視覺呈現（列表化、拿掉厚重卡片）。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function SearchResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlKeyword = searchParams.get('q') || '';
  // 從首頁點機關熱門標籤進來時帶 ?agency=，直接預選該機關篩選（不是當關鍵字比對標題）
  const urlAgency = searchParams.get('agency') || '';

  const savedFilters = useRef(loadFilters()).current;

  const [inputValue, setInputValue] = useState(urlKeyword);
  const [allData, setAllData] = useState([]);
  const [pageLoading, setPageLoading] = useState(true);
  const [selectedAgencies, setSelectedAgencies] = useState(
    urlAgency ? [urlAgency] : (savedFilters.selectedAgencies ?? [])
  );
  const [selectedAmountRanges, setSelectedAmountRanges] = useState(savedFilters.selectedAmountRanges ?? []);
  const [selectedDeadlineRanges, setSelectedDeadlineRanges] = useState(savedFilters.selectedDeadlineRanges ?? []);
  const [favoriteIds, setFavoriteIds] = useState(() => getFavoriteIds());
  const [currentPage, setCurrentPage] = useState(savedFilters.currentPage ?? 1);

  const handleToggleFavorite = (id) => setFavoriteIds(toggleFavorite(id));

  useEffect(() => {
    getAllSubsidy()
      .then(data => {
        setAllData(data);
        setPageLoading(false);
      })
      .catch(err => {
        console.error('載入資料失敗', err);
        setPageLoading(false);
      });
  }, []);

  // 網址上的關鍵字變了（例如從首頁點了不同的熱門標籤），同步輸入框
  useEffect(() => {
    setInputValue(urlKeyword);
  }, [urlKeyword]);

  const agencyCounts = allData.reduce((counts, item) => {
    if (item.category) counts[item.category] = (counts[item.category] || 0) + 1;
    return counts;
  }, {});
  const agencyOptions = Object.keys(agencyCounts).sort((a, b) => agencyCounts[b] - agencyCounts[a]);

  const matchesFilters = (item) => {
    const agencyOk = selectedAgencies.length === 0 || selectedAgencies.includes(item.category);
    const amountOk = selectedAmountRanges.length === 0 || selectedAmountRanges.includes(getAmountBucket(item.amount));
    const deadlineOk = selectedDeadlineRanges.length === 0 || selectedDeadlineRanges.includes(getDeadlineBucket(item.deadline));
    return agencyOk && amountOk && deadlineOk;
  };

  const searchResults = allData.filter(matchesFilters).filter(item => item.title?.includes(urlKeyword));

  const totalPages = Math.max(1, Math.ceil(searchResults.length / ITEMS_PER_PAGE));
  const currentItems = searchResults.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );
  const pageNumbers = getPageNumbers(currentPage, totalPages);

  const submitSearch = () => {
    const trimmed = inputValue.trim();
    if (!trimmed) return;
    setSearchParams({ q: trimmed });
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') submitSearch();
  };

  // 篩選條件或關鍵字一變動，頁碼重置回第一頁
  const isFirstRun = useRef(true);
  useEffect(() => {
    if (isFirstRun.current) {
      isFirstRun.current = false;
      return;
    }
    setCurrentPage(1);
  }, [selectedAgencies, selectedAmountRanges, selectedDeadlineRanges, urlKeyword]);

  // 篩選條件跟頁碼存到 sessionStorage，方便從詳細頁返回時還原
  useEffect(() => {
    try {
      sessionStorage.setItem(FILTER_KEY, JSON.stringify({
        selectedAgencies, selectedAmountRanges, selectedDeadlineRanges, currentPage,
      }));
    } catch {
      // sessionStorage 滿了或被禁用——還原只是體驗優化，失敗就算了
    }
  }, [selectedAgencies, selectedAmountRanges, selectedDeadlineRanges, currentPage]);

  return (
    <div className="page-container" style={{ paddingTop: '32px', paddingBottom: '60px' }}>

      {/* 頂部搜尋框：延續首頁的方正樣式，送出鍵用動詞 */}
      <div style={{ display: 'flex', marginBottom: '24px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search
            size={16}
            strokeWidth={2}
            style={{
              position: 'absolute', left: '13px', top: '50%',
              transform: 'translateY(-50%)', color: 'var(--ink-25)', pointerEvents: 'none',
            }}
          />
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            aria-label="搜尋補助案"
            className="field"
            style={{ paddingLeft: '38px', fontSize: '14.5px', borderRight: 'none', borderRadius: '2px 0 0 2px' }}
          />
        </div>
        <button onClick={submitSearch} className="btn btn-primary" style={{ borderRadius: '0 2px 2px 0', padding: '0 22px' }}>
          搜尋
        </button>
      </div>

      {pageLoading ? (
        <div className="state-block">載入中…</div>
      ) : (
        <>
          <p style={{ color: 'var(--ink-45)', fontSize: '14px', marginBottom: '14px' }}>
            符合條件 <span className="num" style={{ fontWeight: 700, color: 'var(--ink)' }}>{searchResults.length}</span> 件
          </p>

          {/* Filter + Sort：常駐下拉，維持一貫互動 */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            flexWrap: 'wrap', gap: '10px', marginBottom: '20px',
            paddingBottom: '14px', borderBottom: '2px solid var(--ink)',
          }}>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <MultiSelectDropdown
                label="機關"
                options={agencyOptions}
                selectedValues={selectedAgencies}
                onChange={setSelectedAgencies}
              />
              <MultiSelectDropdown
                label="補助金額"
                options={AMOUNT_BUCKETS}
                selectedValues={selectedAmountRanges}
                onChange={setSelectedAmountRanges}
              />
              <MultiSelectDropdown
                label="申請期限"
                options={DEADLINE_BUCKETS}
                selectedValues={selectedDeadlineRanges}
                onChange={setSelectedDeadlineRanges}
              />
            </div>
            <span style={{ fontSize: '13px', color: 'var(--ink-45)' }}>依相關性排序</span>
          </div>

          {currentItems.length === 0 ? (
            <div className="state-block">
              <strong>沒有符合的補助案</strong>
              換個關鍵字，或放寬上方的機關、金額、期限篩選。
            </div>
          ) : (
            <div>
              {currentItems.map((item) => (
                <SubsidyCard
                  key={item.id}
                  item={item}
                  isFavorited={favoriteIds.includes(item.id)}
                  onToggleFavorite={handleToggleFavorite}
                />
              ))}
            </div>
          )}

          {totalPages > 1 && (
            <div style={{
              display: 'flex', justifyContent: 'center', alignItems: 'center',
              gap: '6px', marginTop: '32px',
            }}>
              <button
                onClick={() => setCurrentPage(p => p - 1)}
                disabled={currentPage === 1}
                style={pageButtonStyle(false, currentPage === 1)}
              >
                <ChevronLeft size={15} />
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
                <ChevronRight size={15} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default SearchResultsPage;
