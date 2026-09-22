import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { getAllSubsidy } from '../services/subsidyService';

const HOT_TAG_COUNT = 6;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 首頁只做一件事——搜尋入口。不顯示篩選、不顯示清單、不支援空白瀏覽，
//    像 Google/ChatGPT 首頁那樣，第一眼就知道「這裡是用來搜尋的」。
//    篩選、排序、結果清單全部移到 /search 頁面。
//
//    熱門搜尋標籤改成真實機關（依資料筆數排序取前 6 個），不是關鍵字——
//    這裡順便把資料抓回來（getAllSubsidy 內部有快取，等一下進 /search 頁
//    不會再打第二次），點擊直接帶 ?agency= 到結果頁，預選該機關篩選，
//    而不是拿機關名稱去搜標題（大部分標題本來就不含機關全名，搜了也匹配不到）。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function HomePage() {
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState('');
  const [hotAgencies, setHotAgencies] = useState([]);

  useEffect(() => {
    getAllSubsidy()
      .then((data) => {
        const counts = data.reduce((acc, item) => {
          if (item.category) acc[item.category] = (acc[item.category] || 0) + 1;
          return acc;
        }, {});
        const top = Object.keys(counts)
          .sort((a, b) => counts[b] - counts[a])
          .slice(0, HOT_TAG_COUNT);
        setHotAgencies(top);
      })
      .catch((err) => console.error('載入機關清單失敗', err));
  }, []);

  const goSearch = (q) => {
    const trimmed = q.trim();
    if (!trimmed) return; // 首頁不支援空白瀏覽，沒有關鍵字就不跳頁
    navigate(`/search?q=${encodeURIComponent(trimmed)}`);
  };

  const goAgency = (agency) => {
    navigate(`/search?agency=${encodeURIComponent(agency)}`);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') goSearch(keyword);
  };

  return (
    <div style={{
      minHeight: 'calc(100vh - 60px)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px 20px 80px',
    }}>
      <h1 style={{
        fontSize: '32px',
        fontWeight: '700',
        color: '#1a1a1a',
        textAlign: 'center',
        marginBottom: '12px',
      }}>
        找到適合你的補助案
      </h1>
      <p style={{
        fontSize: '15px',
        color: '#6b7280',
        textAlign: 'center',
        marginBottom: '36px',
      }}>
        用 AI 幫你搜尋、整理、找到適合的政府補助
      </p>

      {/* 搜尋框：首頁最主要的視覺焦點 */}
      <div style={{ width: '100%', maxWidth: '620px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          background: '#fff',
          border: '1px solid #e5e7eb',
          borderRadius: '28px',
          padding: '4px 8px 4px 20px',
          boxShadow: '0 1px 6px rgba(0,0,0,0.04)',
        }}>
          <Search size={19} strokeWidth={1.75} color="#9ca3af" />
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="你想找什麼補助？"
            style={{
              flex: 1,
              border: 'none',
              outline: 'none',
              background: 'transparent',
              padding: '14px 12px',
              fontSize: '16px',
              color: '#1a1a1a',
            }}
          />
          <button
            onClick={() => goSearch(keyword)}
            aria-label="搜尋"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              border: 'none',
              background: '#1a73e8',
              color: '#fff',
              cursor: 'pointer',
              flexShrink: 0,
              transition: 'background 0.15s',
            }}
          >
            <Search size={17} strokeWidth={2} />
          </button>
        </div>

        <p style={{
          textAlign: 'center',
          fontSize: '13px',
          color: '#9ca3af',
          marginTop: '12px',
        }}>
          例如：AI、數位轉型、ESG、節能
        </p>
      </div>

      {/* 熱門搜尋：真實機關（依資料筆數排序），低存在感的 pill，不做成大型 Card */}
      {hotAgencies.length > 0 && (
        <div style={{ marginTop: '40px', textAlign: 'center' }}>
          <p style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '12px' }}>各部門機關搜尋</p>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center', maxWidth: '560px' }}>
            {hotAgencies.map((agency) => (
              <button key={agency} className="pill" onClick={() => goAgency(agency)}>
                {agency}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default HomePage;
