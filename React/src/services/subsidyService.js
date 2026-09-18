// subsidies.enc.json為補助案件的加密版本，大小約 277 KB，放在 public 資料夾裡面。
const DATA_URL = `${process.env.PUBLIC_URL}/subsidies.enc.json`;
const PASSWORD_KEY = 'palentir_unlock_password';

// 本機開發用：設定了這個環境變數（docker-compose.yml 的 react 服務才會有）就直接打
// dev_api.py 拿即時、未加密的資料庫內容，跳過「靜態加密檔+密碼」那一整套。
// 只影響 `npm start`（docker-compose 的環境變數），`deploy_palantir` 是在本機另外
// 執行 `npm run build`、不吃這個環境變數，不會誤打包進正式發布版本。
export const LOCAL_API_URL = process.env.REACT_APP_LOCAL_API_URL || null;

// 分別記錄解密的資料與匯出時間，避免每次都要重新下載/解密
let cachedRows = null;
let cachedExportedAt = null;
let inFlight = null;   // 防止多個頁面同時掛載時重複下載/解密

//因為加密後是一堆位元組，前端要解密前要先把 base64 字串轉回位元組陣列
const b64ToBytes = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

// 把密碼轉成 AES-GCM 的鑰匙，這裡用 PBKDF2 產生鑰匙，跟 Python 端的做法一樣
async function deriveKey(password, salt, iterations) {
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(password),
    'PBKDF2',
    false,
    ['deriveKey']
  );
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations, hash: 'SHA-256' },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['decrypt']
  );
}

//解壓縮
async function gunzip(buffer) {
  const stream = new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'));
  return new Response(stream).arrayBuffer();
}

// 解密信封，回傳明文 JSON 物件
async function decryptEnvelope(envelope, password) {
  const key = await deriveKey(
    password,
    b64ToBytes(envelope.salt),
    envelope.iterations
  );

  // Python 的 AESGCM.encrypt 回傳 ciphertext||tag，正好是 Web Crypto 預期的格式
  let plain = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: b64ToBytes(envelope.iv) },
    key,
    b64ToBytes(envelope.data)
  );

  if (envelope.compression === 'gzip') {
    plain = await gunzip(plain);
  }

  return JSON.parse(new TextDecoder().decode(plain));
}
// 下載信封 JSON，回傳物件
async function fetchEnvelope() {
  const response = await fetch(DATA_URL, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`無法取得資料檔（HTTP ${response.status}）`);
  return response.json();
}

// 解鎖
export async function unlock(password) {
  const envelope = await fetchEnvelope();
  const rows = await decryptEnvelope(envelope, password);   // 密碼錯這裡會丟例外
  
  cachedRows = rows;
  cachedExportedAt = envelope.exported_at || null;
  localStorage.setItem(PASSWORD_KEY, password);
  return rows;
}

// 已經解開過（這個瀏覽器記住了可用的密碼）
export function hasStoredPassword() {
  return !!localStorage.getItem(PASSWORD_KEY);
}

// 用記住的密碼自動解鎖
export async function unlockWithStored() {
  const stored = localStorage.getItem(PASSWORD_KEY);
  if (!stored) throw new Error('沒有記住的密碼');
  try {
    return await unlock(stored);
  } catch (error) {
    localStorage.removeItem(PASSWORD_KEY);
    throw error;
  }
}

// 登出功能
export function lock() {
  localStorage.removeItem(PASSWORD_KEY);
  cachedRows = null;
  cachedExportedAt = null;
  inFlight = null;
}

// 資料匯出時間（信封裡的明文欄位，不用解密就讀得到）
export function getExportedAt() {
  return cachedExportedAt;
}

// 本機開發模式：直接打 dev_api.py，不用密碼、不解密。
async function fetchFromLocalApi() {
  if (cachedRows) return cachedRows;
  if (inFlight) return inFlight;

  inFlight = (async () => {
    try {
      const response = await fetch(LOCAL_API_URL, { cache: 'no-cache' });
      if (!response.ok) throw new Error(`本機API取得資料失敗（HTTP ${response.status}）`);
      const rows = await response.json();
      cachedRows = rows;
      cachedExportedAt = null;   // 本機模式沒有「匯出時間」這個概念，資料本來就是即時的
      return rows;
    } catch (error) {
      console.error('本機API取得資料失敗:', error);
      return [];
    } finally {
      inFlight = null;
    }
  })();

  return inFlight;
}

// 主程式：取得所有補助案件資料，回傳陣列
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export const getAllSubsidy = async () => {
  if (LOCAL_API_URL) return fetchFromLocalApi();

  if (cachedRows) return cachedRows;

  // 多個頁面同時掛載時共用同一個請求，不要重複下載+解密
  if (inFlight) return inFlight;

  //使用 localStorage 記住的密碼解鎖
  const password = localStorage.getItem(PASSWORD_KEY);
  if (!password) {
    // 正常情況下 PasswordGate 會擋在前面，走到這裡代表狀態不同步
    console.error('尚未解鎖，無法取得資料');
    return [];
  }
  //建立並記錄一個 Promise，避免多個頁面同時掛載時重複下載/解密。
  inFlight = (async () => {
    try {
      const envelope = await fetchEnvelope();
      const rows = await decryptEnvelope(envelope, password);
      cachedRows = rows;
      cachedExportedAt = envelope.exported_at || null;
      return rows;
    } catch (error) {
      
      console.error('獲取所有資料失敗:', error);
      localStorage.removeItem(PASSWORD_KEY);
      return [];
    } finally {
      inFlight = null;
    }
  })();

  return inFlight;
};
