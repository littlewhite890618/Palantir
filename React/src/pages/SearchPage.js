import React, { useState, useEffect } from 'react';
import { getAllSubsidy } from '../services/n8nService';
import { useNavigate } from 'react-router-dom';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 這個元件是整個搜尋體驗的指揮官。
//    它不只是一個搜尋框，而是一個「會先幫你準備好所有資料」的智慧助理。
//    資料只拉一次，之後你做什麼操作都不會再去打擾 n8n。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function SearchPage() {

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 🎭 VIBE: 狀態設計 — 這裡在決定「這個頁面需要記住哪些事情」
  //    keyword 是使用者目前打了什麼字
  //    results 是「有沒有搜尋過」的關鍵訊號：null 代表還沒搜尋，[]代表搜了但沒結果
  //    allData 是一次性抓回來的完整資料庫備份，後續的一切都靠它
  //    pageLoading 讓使用者知道「我還沒準備好，等我一下」
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const [keyword, setKeyword] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [allData, setAllData] = useState([]);
  const [pageLoading, setPageLoading] = useState(true);
  const navigate = useNavigate();

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 🚀 VIBE: 頁面一開門就先把貨全搬進來
  //    為什麼？因為我們不想讓使用者每次按搜尋都要等 API。
  //    把資料一口氣拿進 allData，之後所有的篩選都在本地端閃電完成，
  //    使用者感覺像是「即時搜尋」，體驗更流暢。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 📅 VIBE: 「最新」不是指資料最新建立，而是「離今天最近的開始日期」
  //    這樣的邏輯能確保使用者看到的是「現在最有時效性」的補助案，
  //    不是被埋在資料庫深處的老案子。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const sortedLatest = [...allData]
    .sort((a, b) => {
      const today = new Date();
      const diffA = Math.abs(new Date(a.start_date) - today);
      const diffB = Math.abs(new Date(b.start_date) - today);
      return diffA - diffB;
    })
    .slice(0, 5);

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 🔎 VIBE: 搜尋邏輯 — 不出門就能找遍所有角落
  //    因為資料已在 allData 裡，這個函式只是一個過濾器，
  //    跨欄位比對讓使用者不管輸入標題、日期還是金額都能命中，
  //    降低「找不到」的挫折感。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const handleSearch = async () => {
    if (!keyword.trim()) return; // 防止使用者按下空白搜尋，浪費時間
    setLoading(true);
    try {
      const filtered = allData.filter(item =>
        item.title?.includes(keyword) ||
        item.category?.includes(keyword) ||
        item.description?.includes(keyword) ||
        item.start_date?.includes(keyword) ||
        item.deadline?.includes(keyword) ||
        item.amount?.includes(keyword)
      );
      setResults(filtered);
    } catch (error) {
      console.error('搜尋失敗', error);
      setResults([]);
    }
    setLoading(false);
  };

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // ⌨️ VIBE: Enter 鍵是搜尋框的「靈魂」
  //    因為所有人輸入完畢的直覺反應都是按 Enter，
  //    如果沒處理這個事件，使用者會覺得這個搜尋框「壞掉了」。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 🎯 VIBE: 一個變數決定頁面「說哪種故事」
  //    results === null → 還沒搜尋 → 顯示最新補助案（引導探索）
  //    results !== null → 搜尋後   → 顯示搜尋結果（回應需求）
  //    isShowingLatest 是一個語意旗幟，讓後面的 UI 邏輯讀起來更像說人話。
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  const displayList = results !== null ? results : sortedLatest;
  const isShowingLatest = results === null;

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
          口語化的說法讓使用者感受到這個工具是為他們而存在的，而不是冷冰冰的系統。
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
          圖示按鈕在左、清除在右，像一個有眼神的輸入框。
          loading 狀態下換成沙漏，讓使用者感覺「系統有在動」。
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
              {loading ? '⏳' : '🔍'}
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
                onClick={() => { setResults(null); setKeyword(''); }} // 清除時同步重置搜尋結果，回到「最新補助案」狀態
                style={{ padding: '14px 16px', border: 'none', background: 'transparent', cursor: 'pointer', color: '#aaa', fontSize: '18px' }}
              >
                ✕
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          📢 VIBE: 標題會說話，讓使用者知道他現在在哪個情境
          搜尋前：「最新補助案」→ 帶有探索感，居中對齊更像舞台感
          搜尋後：「搜尋結果：共 N 筆」→ 精準回饋，靠左讓視線自然往下掃結果
          一個小小的對齊切換，傳遞了完全不同的資訊密度。
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <h3 style={{ marginBottom: '16px', color: '#555', textAlign: isShowingLatest ? 'center' : 'left' }}>
        {isShowingLatest ? '📢 最新補助案' : `搜尋結果：「${keyword}」共 ${displayList.length} 筆`}
      </h3>

      {/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          📋 VIBE: 補助案卡片 — 讓資訊密度剛剛好
          一張卡片同時給出「是什麼、多少錢、什麼時候」，
          不需要點進去就能快速判斷要不要深入了解。
          下載按鈕藏在右下角，不干擾閱讀，需要時一眼就找到。
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {displayList.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', color: '#888' }}>
          查無相關補助案，請嘗試其他關鍵字
        </div>
      ) : (
        displayList.map((item) => (
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
          ➡️ VIBE: 「顯示更多」只在「最新補助案」模式才出現
          因為搜尋模式已經是「全庫過濾」了，不需要再「更多」。
          這顆按鈕的存在是為了讓有探索慾望的人繼續走下去，
          hover 時反色填滿，像是在說「來，繼續看吧」。
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {isShowingLatest && (
        <div style={{ textAlign: 'center', marginTop: '8px', marginBottom: '40px' }}>
          <button
            onClick={() => navigate('/all')}
            style={{
              padding: '10px 32px', border: '1.5px solid #1a73e8', borderRadius: '8px',
              background: 'transparent', color: '#1a73e8', fontSize: '15px',
              fontWeight: '500', cursor: 'pointer', transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#1a73e8'; e.currentTarget.style.color = 'white'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#1a73e8'; }}
          >
            顯示更多 →
          </button>
        </div>
      )}
    </div>
  );
}

export default SearchPage;
