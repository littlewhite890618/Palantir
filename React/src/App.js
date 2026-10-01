import { HashRouter, Routes, Route, Outlet } from 'react-router-dom';
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
import CalendarPage from './pages/CalendarPage';
// 新案列表（通知鈴鐺的目的地）用一般 import，刻意不像管理台那樣用 NODE_ENV 排除：
// 這頁規劃要跟鈴鐺一起上線給一般使用者，現在排除、之後上線再加回來等於白做兩次。
import NewCasesPage from './pages/NewCasesPage';
import { LOCAL_API_URL } from './services/subsidyService';
// ⚠️ 管理台（新案審核）用 NODE_ENV 判斷（不是 REACT_APP_LOCAL_API_URL），這是刻意的：
// CRA 只保證把 process.env.NODE_ENV 折成字面值，正式 build 會變成
// 'production' === 'production' → 壓縮器把整個 require 分支連同 ReviewPage／AdminLayout
// 的字串一起從 bundle 刪除。REACT_APP_* 沒設定時不會被折疊（實測 2026-09-23），
// 程式碼仍會被打包進正式站——雖然不顯示，但任何人都讀得到審核流程與 API 路徑。
// 執行時是否真的顯示，另外由 LOCAL_API_URL 把關（見下方 Route 與 ReviewPage 本身）。
const isDev = process.env.NODE_ENV !== 'production';
const ReviewPage = isDev ? require('./pages/ReviewPage').default : null;
const AdminLayout = isDev ? require('./components/AdminLayout').default : null;

// 搜尋器（給顧問用的前台）：共用 Navbar。管理台不走這裡，所以搜尋器不會有審核入口。
function MainLayout() {
  return (
    <>
      <Navbar />
      <Outlet />
    </>
  );
}

function App() {
  return (
    <HashRouter>
      {/* 📌 PasswordGate 包在最外層（連 Navbar 都包進去）
          ——沒解開密碼之前，整個站不會渲染任何東西 */}
      <PasswordGate>
        <Routes>
          {/* 管理台：獨立版面、獨立路徑，只在本機開發模式存在（見上方說明） */}
          {AdminLayout && LOCAL_API_URL && (
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<ReviewPage />} />
            </Route>
          )}

          <Route element={<MainLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchResultsPage />} />
            <Route path="/favorites" element={<FavoritesPage />} />
            <Route path="/subsidy/:id" element={<SubsidyDetailPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            {/* 新案列表：跟通知鈴鐺同一個顯示條件（取得到已審核資料才有意義） */}
            {LOCAL_API_URL && <Route path="/new-cases" element={<NewCasesPage />} />}
          </Route>
        </Routes>
      </PasswordGate>
    </HashRouter>
  );
}

export default App;
