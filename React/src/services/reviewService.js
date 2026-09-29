// 審核頁專用的 API 呼叫層。只在本機開發模式有意義：LOCAL_API_URL 是 docker-compose 的
// react 服務才會設的環境變數，deploy_palantir 的 npm run build 不吃它，所以正式版本
// 這裡的 API_BASE 會是 null，審核頁也不會被註冊（見 App.js / Navbar.js）。
import { LOCAL_API_URL } from './subsidyService';

// LOCAL_API_URL 形如 http://localhost:8001/api/subsidies，去掉結尾那段就是 API base。
export const API_BASE = LOCAL_API_URL ? LOCAL_API_URL.replace(/\/api\/subsidies\/?$/, '') : null;

// 後端錯誤一律是 { error: "訊息" }，這裡轉成帶得動訊息的 Error，讓頁面直接顯示原因
// （例如「以下待審 id 不存在或不是 pending」），不要只丟 HTTP 狀態碼給使用者看。
async function request(path, options) {
  if (!API_BASE) throw new Error('目前不是本機開發模式，沒有可用的審核 API');
  const res = await fetch(`${API_BASE}${path}`, options);
  let body = null;
  try {
    body = await res.json();
  } catch {
    // 非 JSON 回應（例如服務沒開、被中間層攔截）→ 下面統一用狀態碼報錯
  }
  if (!res.ok) throw new Error((body && body.error) || `請求失敗（HTTP ${res.status}）`);
  return body;
}

// 待審新案；有疑似舊案的會多一個 suspected_dup 物件（舊案的 id/標題/機關/金額/截止日/連結）
export function fetchPending() {
  return request('/api/pending', { cache: 'no-cache' });
}

// 最近一次管線執行摘要；沒跑過會回 { exists: false }
export function fetchRunSummary() {
  return request('/api/run-summary', { cache: 'no-cache' });
}

const postId = (path, id) => request(path, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ id }),
});

// 核准：寫入正式表 subsidies，待審記錄標記 approved
export const approvePending = (id) => postId('/api/pending/approve', id);

// 退回：只標記 rejected，不寫正式表；之後管線再抓到同一筆也會跳過
export const rejectPending = (id) => postId('/api/pending/reject', id);
