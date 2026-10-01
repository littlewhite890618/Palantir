import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { getAllSubsidy } from '../services/subsidyService';

const AGENCY_INDEX_COUNT = 8;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 首頁只做一件事——搜尋入口。不顯示清單、不支援空白瀏覽。
//
//    版面刻意不置中。置中大標＋圓角搜尋框是每個工具網站都長的樣子；
//    這裡改成靠左的「卷宗封面」：抬頭、收錄概況（真實筆數與機關數，等寬數字）、
//    搜尋欄、機關索引。概況那行是本頁的主角——它用真實資料說明「這裡收了什麼」，
//    比任何一句行銷標語都具體。
//
//    機關索引用清單而不是一排 pill：每個機關後面接等寬的件數，像目錄頁的頁碼，
//    掃一眼就知道哪個機關案子多。點擊直接帶 ?agency= 預選篩選，
//    而不是拿機關名稱去搜標題（標題多半不含機關全名，搜了也匹配不到）。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function HomePage() {
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState('');
  const [stats, setStats] = useState(null);

  useEffect(() => {
    getAllSubsidy()
      .then((data) => {
        const counts = data.reduce((acc, item) => {
          if (item.category) acc[item.category] = (acc[item.category] || 0) + 1;
          return acc;
        }, {});
        const ranked = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
        setStats({
          total: data.length,
          agencyCount: ranked.length,
          index: ranked.slice(0, AGENCY_INDEX_COUNT).map((name) => ({ name, count: counts[name] })),
        });
      })
      .catch((err) => console.error('載入補助案資料失敗', err));
  }, []);

  const goSearch = (q) => {
    const trimmed = q.trim();
    if (!trimmed) return; // 首頁不支援空白瀏覽，沒有關鍵字就不跳頁
    navigate(`/search?q=${encodeURIComponent(trimmed)}`);
  };

  const goAgency = (agency) => navigate(`/search?agency=${encodeURIComponent(agency)}`);

  return (
    <div className="page-container" style={{ paddingTop: '64px', paddingBottom: '80px' }}>
      <h1 style={{ fontSize: '38px', lineHeight: 1.3, marginBottom: '14px', maxWidth: '18ch' }}>
        政府補助案查詢
      </h1>

      {/* 收錄概況：本頁的主角。真實資料，不是文案 */}
      <p style={{ fontSize: '15px', color: 'var(--ink-70)', marginBottom: '34px', maxWidth: '52ch' }}>
        {stats ? (
          <>
            目前收錄 <span className="num" style={{ fontWeight: 700, color: 'var(--ink)' }}>{stats.total}</span> 件補助案，
            涵蓋 <span className="num" style={{ fontWeight: 700, color: 'var(--ink)' }}>{stats.agencyCount}</span> 個機關。
            輸入關鍵字開始查詢。
          </>
        ) : '載入收錄概況…'}
      </p>

      {/* 搜尋欄：方正、與送出鍵接成一體，送出鍵用動詞而不是箭頭 */}
      <div style={{ display: 'flex', maxWidth: '640px', marginBottom: '10px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search
            size={17}
            strokeWidth={2}
            style={{
              position: 'absolute', left: '14px', top: '50%',
              transform: 'translateY(-50%)', color: 'var(--ink-25)', pointerEvents: 'none',
            }}
          />
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') goSearch(keyword); }}
            placeholder="例如：數位轉型、節能設備、人才培訓"
            aria-label="搜尋補助案"
            className="field"
            style={{ paddingLeft: '40px', borderRight: 'none', borderRadius: '2px 0 0 2px' }}
          />
        </div>
        <button
          onClick={() => goSearch(keyword)}
          className="btn btn-primary"
          style={{ borderRadius: '0 2px 2px 0', padding: '0 26px' }}
        >
          搜尋
        </button>
      </div>

      {/* 機關索引：清單＋等寬件數，像目錄頁的頁碼 */}
      {stats && stats.index.length > 0 && (
        <div style={{ marginTop: '52px', maxWidth: '640px' }}>
          <h2 style={{
            fontSize: '15px', paddingBottom: '8px', marginBottom: '2px',
            borderBottom: '2px solid var(--ink)',
          }}>
            依機關瀏覽
          </h2>

          {stats.index.map(({ name, count }) => (
            <button
              key={name}
              onClick={() => goAgency(name)}
              style={{
                display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
                width: '100%', gap: '16px', padding: '11px 2px',
                border: 'none', borderBottom: '1px solid var(--rule)',
                background: 'transparent', cursor: 'pointer', textAlign: 'left',
              }}
            >
              <span style={{ fontSize: '14.5px' }}>{name}</span>
              <span className="num" style={{ fontSize: '13px', color: 'var(--ink-45)', flexShrink: 0 }}>
                {count} 件
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default HomePage;
