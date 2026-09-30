import { LOCAL_API_URL } from './subsidyService';

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🧠 VIBE: 通知鈴鐺的未讀數 = 「審核通過時間比我上次看通知還晚」的筆數。
//    刻意不用資料庫旗標（例如在 subsidies_pending 加一個 0/1 欄位）：
//    旗標是全域共享的，任何一台電腦點開鈴鐺就會把別人的未讀狀態一起清掉，
//    而且要多開一個寫入端點；正式站是靜態站、沒有後端可以呼叫，那條路走不通。
//    改用「上次已讀時間」存在各自瀏覽器，純讀取就能算，之後要延伸到正式站
//    （把 reviewed_at 一併匯出）這套邏輯不用改。
//
//    只算「經過管理台審核通過」的案子：API 是查 subsidies_pending 的 approved
//    記錄，8/22 那批繞過審核流程直接寫進正式表的舊資料在待審表裡沒有紀錄，
//    天然不會被算進未讀數。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const LAST_SEEN_KEY = 'palentir_notif_last_seen';
// 前一次的已讀時間：新案列表要顯示「剛才通知的那批」，但點鈴鐺當下 LAST_SEEN 就被推到
// 「現在」了，用它去算一定是 0 筆。所以覆蓋前先把舊值留在這裡，列表頁改用它當分界。
const PREV_SEEN_KEY = 'palentir_notif_prev_seen';

// LOCAL_API_URL 形如 http://localhost:8001/api/subsidies，去掉結尾那段就是 API base。
const API_BASE = LOCAL_API_URL ? LOCAL_API_URL.replace(/\/api\/subsidies\/?$/, '') : null;

// 已審核通過的清單（每筆含 title、category、reviewed_at），依審核時間新到舊
export async function fetchApproved() {
  if (!API_BASE) throw new Error('目前沒有可用的通知資料來源');
  const res = await fetch(`${API_BASE}/api/approved`, { cache: 'no-cache' });
  let body = null;
  try {
    body = await res.json();
  } catch {
    // 非 JSON 回應（服務沒開、被中間層攔截）→ 下面統一用狀態碼報錯
  }
  if (!res.ok) throw new Error((body && body.error) || `請求失敗（HTTP ${res.status}）`);
  return body || [];
}

// 上次看通知的時間；沒有紀錄（第一次用、或清過瀏覽器資料）回 null，代表全部都算未讀
export function getLastSeen() {
  try {
    return localStorage.getItem(LAST_SEEN_KEY) || null;
  } catch (error) {
    console.error('讀取通知已讀時間失敗', error);
    return null;
  }
}

// 前一次的已讀時間；沒有紀錄回 null，代表「還沒讀過任何一批」
export function getPrevLastSeen() {
  try {
    return localStorage.getItem(PREV_SEEN_KEY) || null;
  } catch (error) {
    console.error('讀取前一次通知已讀時間失敗', error);
    return null;
  }
}

// 點開鈴鐺時呼叫：把「現在」記成上次已讀時間，之後只有比這更晚審核通過的才算新。
// 覆蓋前先把舊值搬到 PREV_SEEN_KEY，新案列表才知道「剛才通知的是哪一批」。
export function markSeen() {
  try {
    const prev = localStorage.getItem(LAST_SEEN_KEY);
    if (prev) localStorage.setItem(PREV_SEEN_KEY, prev);
    else localStorage.removeItem(PREV_SEEN_KEY);   // 首次已讀：前次為「從未讀過」＝顯示全部
    localStorage.setItem(LAST_SEEN_KEY, new Date().toISOString());
  } catch (error) {
    console.error('寫入通知已讀時間失敗', error);
  }
}

// 新案列表要顯示的那批：審核時間晚於「前一次已讀時間」的案子。
// 沒有前次紀錄（從未讀過、或清過瀏覽器資料）就回全部，跟鈴鐺首次把全部算成未讀一致。
export function filterLatestBatch(rows) {
  if (!Array.isArray(rows)) return [];
  const prev = getPrevLastSeen();
  if (!prev) return rows;
  const prevTime = new Date(prev).getTime();
  return rows.filter((r) => {
    const t = new Date(r.reviewed_at).getTime();
    return !isNaN(t) && t > prevTime;
  });
}

// 未讀筆數：reviewed_at 晚於上次已讀時間的筆數。沒有已讀紀錄就全部算未讀。
export function countUnread(rows) {
  if (!Array.isArray(rows)) return 0;
  const lastSeen = getLastSeen();
  if (!lastSeen) return rows.length;
  const lastSeenTime = new Date(lastSeen).getTime();
  return rows.filter((r) => {
    const t = new Date(r.reviewed_at).getTime();
    return !isNaN(t) && t > lastSeenTime;
  }).length;
}
