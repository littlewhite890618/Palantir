import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { getAllSubsidy } from '../services/subsidyService';
import { parseLatestFullDate } from '../utils/deadline';

const pad2 = (n) => String(n).padStart(2, '0');

// 用本地時間組 key；toISOString() 是 UTC，台灣時區會把日期往前推一天
const dateKey = (d) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;

// 回傳 [{ monthKey, label, days: [{ key, date, items }] }]，月份與日期都由早到晚
function groupByDeadline(rows) {
  const months = new Map();
  for (const item of rows) {
    const d = parseLatestFullDate(item.deadline);
    if (!d) continue;
    const monthKey = dateKey(d).slice(0, 7);
    if (!months.has(monthKey)) {
      months.set(monthKey, { monthKey, label: `${d.getFullYear()} 年 ${d.getMonth() + 1} 月`, days: new Map() });
    }
    const days = months.get(monthKey).days;
    const key = dateKey(d);
    if (!days.has(key)) days.set(key, { key, date: d, items: [] });
    days.get(key).items.push(item);
  }
  return [...months.values()]
    .sort((a, b) => a.monthKey.localeCompare(b.monthKey))
    .map((m) => ({ ...m, days: [...m.days.values()].sort((a, b) => a.key.localeCompare(b.key)) }));
}

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];

function DayModal({ day, onClose }) {
  const navigate = useNavigate();

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const d = day.date;
  return (
    <div className="cal-modal-backdrop" onClick={onClose}>
      <div
        className="cal-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`${dateKey(d)} 截止的補助案`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="cal-modal-head">
          <div>
            <div className="cal-modal-date num">{d.getFullYear()}/{d.getMonth() + 1}/{d.getDate()}（{WEEKDAYS[d.getDay()]}）</div>
            <div className="cal-modal-sub">{day.items.length} 件補助案於本日截止</div>
          </div>
          <button className="cal-modal-close" onClick={onClose} title="關閉" aria-label="關閉">
            <X size={18} strokeWidth={1.75} />
          </button>
        </div>
        <ul className="cal-modal-list">
          {day.items.map((item) => (
            <li key={item.id}>
              <button className="cal-modal-row" onClick={() => navigate(`/subsidy/${item.id}`)}>
                <span className="cal-modal-id num">No.{String(item.id).padStart(4, '0')}</span>
                <span className="cal-modal-title">{item.title}</span>
                <span className="cal-modal-agency">{item.category}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function CalendarPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [openDay, setOpenDay] = useState(null);

  useEffect(() => {
    getAllSubsidy()
      .then((data) => setRows(data))
      .catch((err) => {
        console.error('載入資料失敗', err);
        setError(true);
      })
      .finally(() => setLoading(false));
  }, []);

  const months = useMemo(() => groupByDeadline(rows), [rows]);
  const closeModal = useCallback(() => setOpenDay(null), []);

  // 目前月份放網址 ?m=YYYY-MM：從詳細頁返回時自然還原
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get('m');
  let monthIndex = months.findIndex((m) => m.monthKey === requested);
  if (monthIndex === -1) {
    const thisMonth = dateKey(new Date()).slice(0, 7);
    monthIndex = months.findIndex((m) => m.monthKey >= thisMonth);
    if (monthIndex === -1) monthIndex = months.length - 1;
  }
  const current = months[monthIndex];
  const goTo = (i) => setSearchParams({ m: months[i].monthKey }, { replace: true });

  const shell = (children) => (
    <div className="page-container" style={{ paddingTop: '26px', paddingBottom: '70px' }}>{children}</div>
  );

  if (loading) return shell(<div className="state-block">載入中…</div>);
  if (error) return shell(<div className="state-block"><strong>資料載入失敗</strong>請重新整理頁面再試一次。</div>);

  return shell(
    <>
      <button onClick={() => navigate(-1)} className="btn-quiet">
        <ChevronLeft size={15} strokeWidth={2} /> 返回
      </button>

      <div className="page-head">
        <h2>截止日行事曆</h2>
        <p className="page-head-note">只列出有補助案截止的日期，點日期查看當天截止的案子</p>
      </div>

      {months.length === 0 ? (
        <div className="state-block">
          <strong>目前沒有可顯示的截止日</strong>
          補助案的截止日若只寫「額滿為止」或只有年月，不會出現在行事曆上。
        </div>
      ) : (
        <section className="cal-month">
          {/* 箭頭只在「有案子的月份」之間跳，空月份不會出現 */}
          <div className="cal-month-nav">
            <button
              className="cal-month-arrow"
              onClick={() => goTo(monthIndex - 1)}
              disabled={monthIndex === 0}
              title="上一個有截止案的月份"
              aria-label="上一個有截止案的月份"
            >
              <ChevronLeft size={20} strokeWidth={1.75} />
            </button>
            <h3 className="cal-month-label">{current.label}</h3>
            <button
              className="cal-month-arrow"
              onClick={() => goTo(monthIndex + 1)}
              disabled={monthIndex === months.length - 1}
              title="下一個有截止案的月份"
              aria-label="下一個有截止案的月份"
            >
              <ChevronRight size={20} strokeWidth={1.75} />
            </button>
          </div>
          <div className="cal-grid">
            {current.days.map((day) => (
              <button key={day.key} className="cal-day" onClick={() => setOpenDay(day)}>
                <span className="cal-day-num num">{day.date.getDate()}</span>
                <span className="cal-day-week">週{WEEKDAYS[day.date.getDay()]}</span>
                <span className="cal-day-count"><span className="num">{day.items.length}</span> 件</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {openDay && <DayModal day={openDay} onClose={closeModal} />}
    </>
  );
}

export default CalendarPage;
