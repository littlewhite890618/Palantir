import React, { useState, useEffect } from 'react';
// ✅ useEffect 直接 import 進來，而不是用 React.useEffect
// 因為這是 React 官方建議的寫法，閱讀起來更乾淨，也不容易出現 hook 找不到的錯誤

import { getAllSubsidy } from '../services/n8nService';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 這個元件是「補助案全覽室」。
//    它不像搜尋頁那樣被動等使用者提問，
//    而是主動展開所有資料，讓使用者用「分類篩選 + 翻頁」的方式慢慢逛，
//    像是逛展覽，而不是查資料。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🏷️ VIBE: 類別是固定寫死的，因為它代表「這個平台決定服務哪些族群」
//    改動這裡等於改動平台定位，所以不從 API 動態拉，而是直接寫明在程式裡。
//    「全部」永遠擺第一個，因為它是重置鍵，也是最安全的預設值。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const categories = ['全部', '數位轉型', '農業', '環境', '創業', '文創'];

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 📏 VIBE: 每頁 5 筆是一個「不讓人滾太久、又不讓人覺得太少」的黃金數字
//    抽成常數是為了之後只改一個地方就能調整，而不是在程式裡四處找數字 5
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const ITEMS_PER_PAGE = 5;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🔢 VIBE: 頁碼的「省略號邏輯」是為了保護使用者的注意力
//    頁數少時全部顯示沒問題，但如果有 50 頁全顯示出來，
//    使用者的眼睛會不知道該看哪裡。
//    這個函式確保永遠只顯示「當前頁附近 ± 1」+ 首尾頁，
//    中間跳過的地方用「...」代替，乾淨又不失方向感。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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

function AllSubsidyPage() {

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 🎭 VIBE: 狀態設計 — 這個頁面需要記住「完整資料、目前類別、現在第幾頁、還在載入嗎」
  //    這四件事彼此牽連：資料變了影響總頁數，類別切換時頁碼要歸零，
  //    loading 為 true 時整個 UI 先凍結，等資料準備好才開放互動。
  //    ⚠️ useState 必須放在 function 元件裡面，放外面 React 會報錯，
  //    因為 hook 的機制需要依附在元件的生命週期上才能運作。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const [allSubsidies, setAllSubsidies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('全部');
  const [currentPage, setCurrentPage] = useState(1);

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 🚀 VIBE: 頁面一開門就去 n8n 拿全部資料
  //    為什麼在這裡拿而不是點選類別再拿？
  //    因為分類是在前端做的，資料都在本地過濾，
  //    讓切換類別像開燈一樣即時，不需要等 API。
  //    catch 的存在是防呆：就算 n8n 掛了，頁面也不會永遠卡在載入中。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  useEffect(() => {
    getAllSubsidy()
      .then(data => {
        setAllSubsidies(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('取得資料失敗', err);
        setLoading(false);
      });
  }, []);

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 🔽 VIBE: 篩選邏輯 — 「全部」是特例，其他的都是嚴格配對
  //    這一行決定了「使用者選的類別」對應到「要顯示哪些資料」
  //    filtered 是整個下游分頁邏輯的源頭，它一變，totalPages 和 currentItems 都跟著變
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const filtered = activeCategory === '全部'
    ? allSubsidies
    : allSubsidies.filter((item) => item.category === activeCategory);

  const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE);

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 🔄 VIBE: 切換類別時必須把頁碼重置為第 1 頁
  //    為什麼？假設使用者在第 3 頁切換類別，但新類別只有 1 頁，
  //    頁面就會空白，使用者完全不知道發生什麼事。
  //    把 setCurrentPage(1) 綁在 handleCategoryChange 裡，讓這個邏輯永遠成對執行。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const handleCategoryChange = (cat) => {
    setActiveCategory(cat);
    setCurrentPage(1);
  };

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // ✂️ VIBE: slice 是分頁的核心刀法
  //    第 N 頁要顯示的資料 = filtered 陣列從「(N-1)*5」切到「N*5」
  //    這樣不管幾頁，公式都通用，不需要為每一頁寫不同邏輯。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const currentItems = filtered.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const pageNumbers = getPageNumbers(currentPage, totalPages);

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 🎨 VIBE: 頁碼按鈕的樣式是「狀態決定外觀」的縮影
  //    當前頁 → 藍底白字（你在這裡）
  //    可點擊 → 白底黑字（你可以去這裡）
  //    不可點擊 → 灰字 + 禁用游標（這裡你現在去不了）
  //    把三種狀態封裝成一個函式，讓每顆按鈕只說「我是哪種狀態」，
  //    而不是每顆都自己算樣式。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
  // ⏳ VIBE: 資料還沒到之前，整個 UI 先讓路
  //    如果跳過這個判斷直接 render，使用者會看到空白列表以為資料真的是空的，
  //    產生「這個平台沒東西」的錯誤印象。
  //    用 loading 守門，確保使用者第一眼看到的是「有內容的頁面」。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', marginTop: '100px', color: '#888' }}>
        載入中...
      </div>
    );
  }

  return (
    <div className="page-container">

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          🏷️ VIBE: 類別按鈕是使用者的「第一個選擇動作」
          選中的類別用藍底白字凸顯，讓使用者隨時都知道自己在哪個視角看資料。
          點擊時呼叫 handleCategoryChange 確保頁碼同步歸零，避免空白頁的窘境。
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '24px' }}>
        {categories.map((cat) => (
          <button
            key={cat}
            className="btn"
            onClick={() => handleCategoryChange(cat)}
            style={{
              background: activeCategory === cat ? '#1a73e8' : '#f1f3f4',
              color: activeCategory === cat ? 'white' : '#333',
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          📊 VIBE: 「共 N 筆，第 X / Y 頁」是使用者的方位感
          它不是裝飾，而是讓使用者知道「我還有多少東西沒看到」，
          避免翻頁翻到迷路不知道還要翻多久。
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <p style={{ color: '#888', marginBottom: '16px', fontSize: '14px' }}>
        共 {filtered.length} 筆補助案，第 {currentPage} / {totalPages} 頁
      </p>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          📋 VIBE: 補助案卡片 — 資訊密度剛剛好，不用點進去就能快速判斷
          顯示補助區間（startDate ～ deadline）與搜尋頁格式統一，
          讓使用者在兩個頁面之間切換時不會有「格式不同」的認知落差。
          空資料時主動提示，不讓使用者面對無聲的空白。
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {currentItems.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', color: '#888' }}>
          目前沒有補助案資料
        </div>
      ) : (
        currentItems.map((item) => (
          <div className="card" key={item.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <h4 style={{ fontSize: '18px', marginBottom: '8px' }}>{item.title}</h4>
              <span className="tag">{item.category}</span>
            </div>
            <p style={{ color: '#666', marginBottom: '12px' }}>{item.description}</p>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '14px', color: '#888' }}>
                <span>📅 補助期限：{item.deadline}</span>
                <span>💰 {item.amount}</span>
              </div>
              <button
                onClick={() => alert(`下載：${item.title}`)}
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '18px', color: '#1a73e8', padding: '0' }}
                title="下載補助案資料"
              >
                ⬇️
              </button>
            </div>
          </div>
        ))
      )}

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          🔢 VIBE: 分頁列只有「超過一頁」才出現
          因為只有一頁時顯示換頁按鈕毫無意義，反而增加視覺雜訊。
          ◀ / ▶ 箭頭在邊界時自動 disabled，防止使用者翻到不存在的頁面。
          「...」省略號只是視覺佔位，不能點（disabled），
          這樣使用者不會困惑「為什麼點了沒反應」。
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

export default AllSubsidyPage;