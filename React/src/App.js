import { HashRouter, Routes, Route } from 'react-router-dom';
// 📌 HashRouter、Routes、Route 是頁面切換工具
// 就像電梯控制系統，負責決定按哪個按鈕要去哪個樓層
//
// ⚠️ 用 HashRouter 而不是 BrowserRouter，網址會長成 /#/subsidy/123。
// 因為這個站部署在 GitHub Pages，那裡沒有後端可以把所有路徑導向 index.html。
// 用 BrowserRouter 的話，直接開 /subsidy/123 或在詳細頁按重新整理都會 404。
// # 後面的部分永遠不會送給伺服器，所以伺服器每次都只收到 /，乖乖回傳 index.html，
// 剩下的交給 React 自己判斷要顯示哪一頁。

import Navbar from './components/Navbar';
import PasswordGate from './components/PasswordGate';
import HomePage from './pages/HomePage';
import SearchResultsPage from './pages/SearchResultsPage';
import FavoritesPage from './pages/FavoritesPage';
import SubsidyDetailPage from './pages/SubsidyDetailPage';

function App() {
  return (
    <HashRouter>
      {/* 📌 PasswordGate 包在最外層（連 Navbar 都包進去）
          ——沒解開密碼之前，整個站不會渲染任何東西 */}
      <PasswordGate>
        <Navbar />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchResultsPage />} />
          <Route path="/favorites" element={<FavoritesPage />} />
          <Route path="/subsidy/:id" element={<SubsidyDetailPage />} />
        </Routes>
      </PasswordGate>
    </HashRouter>
  );
}

export default App;
