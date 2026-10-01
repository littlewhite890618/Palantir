// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🐛 BUG FIX（2026-09-29）：deadline 是自由文字，多為民國年（「115年5月5日」
// 「115/5/5」），JS 的 `new Date(deadline)` 完全看不懂民國年：
//   - 「115年5月5日」這種中文格式 → 直接判定 Invalid Date → NaN → 所有
//     `diffDays < N` 比較都是 false → 掉到最後一條 return，誤歸類成
//     「90天以上（長期）」，把早就過期的計畫當成還很久才到期。
//   - 「115/5/5」這種斜線格式 → 更糟，會被硬解成西元 115 年（把民國年當
//     西元年讀），diffDays 變成負幾十萬天，「巧合地」落在「已截止」，
//     邏輯完全是錯的、只是結果看起來沒問題。
// 實測 112 筆有填 deadline 的資料，只有 1 筆是標準西元格式能被正確解析。
//
// 修法：比對前先用跟後端 postprocess.py::latest_date() 相同的邏輯（正則抓
// 「年/月/日」，數字<1911 視為民國年 +1911 轉西元，字串內有多個日期取最晚
// 那個代表這列，例如「第一梯115/3/31；第二梯115/6/1」取 6/1）解析成西元
// Date 物件，前後端用同一套判斷準則，不再各自猜測。
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export const DATE_FULL = /(\d{2,4})\s*[年/.\-]\s*(\d{1,2})\s*[月/.\-]\s*(\d{1,2})/g;
export const DATE_YM = /(\d{2,4})\s*[年/.\-]\s*(\d{1,2})\s*月/g;
export const DATE_Y = /(\d{2,4})\s*年/g;

// 民國轉西元：<1911 視為民國年（跟 postprocess.py::_greg() 同款規則）
export const toGregorianYear = (y) => (y < 1911 ? y + 1911 : y);

// 字串裡可能有多個日期（分梯次公告），取「最晚」的那個代表這一列
export function parseLatestDeadline(s) {
  if (!s) return null;
  let best = null;
  const consider = (y, m, d) => {
    const t = new Date(toGregorianYear(y), m - 1, d).getTime();
    if (best === null || t > best) best = t;
  };
  for (const m of s.matchAll(DATE_FULL)) consider(+m[1], +m[2], +m[3]);
  if (best === null) for (const m of s.matchAll(DATE_YM)) consider(+m[1], +m[2], 1);
  if (best === null) for (const m of s.matchAll(DATE_Y)) consider(+m[1], 1, 1);
  return best === null ? null : new Date(best);
}

// 只認「年月日俱全」的日期，取最晚的一個；只有年月/只有年的不推測成 1 號，直接回 null。
// 行事曆用這支：把「115年6月」畫在 6/1 會讓人以為真的 6/1 截止。
export function parseLatestFullDate(s) {
  if (!s) return null;
  let best = null;
  for (const m of s.matchAll(DATE_FULL)) {
    const t = new Date(toGregorianYear(+m[1]), +m[2] - 1, +m[3]).getTime();
    if (best === null || t > best) best = t;
  }
  return best === null ? null : new Date(best);
}
