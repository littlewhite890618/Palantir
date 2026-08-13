const FAVORITES_KEY = 'palentir_favorite_ids';

// 收藏清單的存取邏輯，使用 localStorage 儲存一個陣列，裡面放所有被收藏的補助案 id。
export function getFavoriteIds() {
  try {
    const raw = localStorage.getItem(FAVORITES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (error) {
    console.error('讀取收藏清單失敗', error);
    return [];
  }
}
//判斷某個補助案是否在收藏清單裡
export function isFavorited(id) {
  return getFavoriteIds().includes(id);
}
//
export function toggleFavorite(id) {
  const current = getFavoriteIds();
  const next = current.includes(id)
    ? current.filter((favId) => favId !== id)
    : [...current, id];
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(next));
  return next;
}
