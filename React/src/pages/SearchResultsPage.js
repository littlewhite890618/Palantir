import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { getAllSubsidy } from '../services/subsidyService';
import { getFavoriteIds, toggleFavorite } from '../services/favoritesService';
import MultiSelectDropdown from '../components/MultiSelectDropdown';
import SubsidyCard from '../components/SubsidyCard';

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

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🐛 BUG FIX（2026-09-29）：deadline 是自由文字，多為民國年（「115年5月5日」
// 「115/5/5」），JS 的 `new Date(deadline)` 完全看不懂民國年：
//   - 「115年5月5日」這種中文格式 → 直接判定 Invalid Date → NaN → 所有
//     `diffDays < N` 比較都是 false → 掉到最後一條 return，誤歸類成
//     「90天以上（長期）」，把早就過期的計畫當成還很久才到期。
//   - 「115/5/5」這種斜線格式 → 更糟，會被硬解成西元 115 年（把民國年當
//     西元年讀），diffDays 變成負幾十萬天，「巧合地」落在「已截止」，
//     邏輯完全是錯的、只是結果看起來沒問題。
// 實測 112 筆有填 deadline 的資料，只有 1 筆是標準西元格式能被正確解析。
//
// 修法：比對前先用跟後端 postprocess.py::latest_date() 相同的邏輯（正則抓
// 「年/月/日」，數字<1911 視為民國年 +1911 轉西元，字串內有多個日期取最晚
// 那個代表這列，例如「第一梯115/3/31；第二梯115/6/1」取 6/1）解析成西元
// Date 物件，前後端用同一套判斷準則，不再各自猜測。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const DATE_FULL = /(\d{2,4})\s*[年/.\-]\s*(\d{1,2})\s*[月/.\-]\s*(\d{1,2})/g;
const DATE_YM = /(\d{2,4})\s*[年/.\-]\s*(\d{1,2})\s*月/g;
const DATE_Y = /(\d{2,4})\s*年/g;

// 民國轉西元：<1911 視為民國年（跟 postprocess.py::_greg() 同款規則）
const toGregorianYear = (y) => (y < 1911 ? y + 1911 : y);

// 字串裡可能有多個日期（分梯次公告），取「最晚」的那個代表這一列
function parseLatestDeadline(s) {
  if (!s) return null;
  let best = null;
  const consider = (y, m, d) => {
    const t = new Date(toGregorianYear(y), m - 1, d).getTime();
    if (best === null || t > best) best = t;
  };
  for (const m of s.matchAll(DATE_FULL)) consider(+m[1], +m[2], +m[3]);
  if (best === null) for (const m of s.matchAll(DATE_YM)) consider(+m[1], +m[2], 1);
  if (best === null) for (const m of s.matchAll(DATE_Y)) consider(+m[1], 1, 1);
  return best === null ? null : new Date(best);
}

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
  padding: '0 6px',
  border: isActive ? '1px solid #1a73e8' : '1px solid #e5e7eb',
  borderRadius: '8px',
  background: isActive ? '#1a73e8' : 'white',
  color: isActive ? 'white' : isDisabled ? '#ccc' : '#374151',
  cursor: isDisabled ? 'not-allowed' : 'pointer',
  fontSize: '13px',
  fontWeight: isActive ? '600' : '400',
  transition: 'all 0.15s',
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
    <div style={{ maxWidth: '760px', margin: '0 auto', padding: '32px 20px 60px' }}>

      {/* 頂部搜尋框：延續首頁的搜尋動作，維持同一套視覺語言 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        background: '#fff',
        border: '1px solid #e5e7eb',
        borderRadius: '24px',
        padding: '4px 6px 4px 18px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.03)',
        marginBottom: '20px',
      }}>
        <Search size={17} strokeWidth={1.75} color="#9ca3af" />
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          style={{
            flex: 1, border: 'none', outline: 'none', background: 'transparent',
            padding: '12px 10px', fontSize: '15px', color: '#1a1a1a',
          }}
        />
        <button
          onClick={submitSearch}
          aria-label="搜尋"
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: '34px', height: '34px', borderRadius: '50%', border: 'none',
            background: '#1a73e8', color: '#fff', cursor: 'pointer', flexShrink: 0,
          }}
        >
          <Search size={15} strokeWidth={2} />
        </button>
      </div>

      {pageLoading ? (
        <div style={{ textAlign: 'center', marginTop: '80px', color: '#9ca3af' }}>載入中...</div>
      ) : (
        <>
          <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '16px' }}>
            找到 {searchResults.length} 個可能符合的補助案
          </p>

          {/* Filter + Sort：常駐下拉，維持一貫互動 */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            flexWrap: 'wrap', gap: '10px', marginBottom: '20px',
            paddingBottom: '16px', borderBottom: '1px solid #eef0f2',
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
            <span style={{ fontSize: '13px', color: '#9ca3af' }}>排序：相關性</span>
          </div>

          {currentItems.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#9ca3af', padding: '60px 0' }}>
              查無相關補助案，請嘗試其他關鍵字
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
