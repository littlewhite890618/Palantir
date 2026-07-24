import { BrowserRouter, Routes, Route } from 'react-router-dom';
// 📌 BrowserRouter、Routes、Route 是頁面切換工具
// 就像電梯控制系統，負責決定按哪個按鈕要去哪個樓層

import Navbar from './components/Navbar';
import SearchPage from './pages/SearchPage';
import AllSubsidyPage from './pages/AllSubsidyPage';

function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/all" element={<AllSubsidyPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;