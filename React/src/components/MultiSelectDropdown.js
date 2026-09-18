import React, { useState } from 'react';

// 機關、金額和期限的多選下拉選單元件，因為三個元件功能相同，所以共同一個元件
//傳進來的參數為Props: label、options、selectedValues、onChange
function MultiSelectDropdown({ label, options, selectedValues, onChange }) {
  const [isOpen, setIsOpen] = useState(false);

  //切換某個選項的勾選狀態
  const toggleOption = (option) => {
    if (selectedValues.includes(option)) {
      onChange(selectedValues.filter((v) => v !== option));
    } else {
      onChange([...selectedValues, option]);
    }
  };

  //篩選器選擇的數量，若有選擇則顯示ex:機關(2)，否則顯示ex:機關
  const buttonLabel = selectedValues.length > 0
    ? `${label}（${selectedValues.length}）`
    : label;

  return (
    <div style={{ position: 'relative' }}>
      <button
        className="btn"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          background: selectedValues.length > 0 ? '#e8f0fe' : '#f1f3f4',
          color: selectedValues.length > 0 ? '#1a73e8' : '#333',
        }}
      >
        {buttonLabel} ▾
      </button>
      {/* 展開後的選項清單 */}
      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '48px',
          left: 0,
          minWidth: '220px',
          maxHeight: '320px',
          overflowY: 'auto',
          background: 'white',
          borderRadius: '12px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
          border: '1px solid #eee',
          zIndex: 200,
          padding: '8px 0',
        }}>
          {options.map((option) => (
            <label
              key={option}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                cursor: 'pointer',
                fontSize: '14px',
                color: '#333',
              }}
            >
              <input
                type="checkbox"
                checked={selectedValues.includes(option)}
                onChange={() => toggleOption(option)}
              />
              {option}
            </label>
          ))}
        </div>
      )}

      {isOpen && (
        <div
          onClick={() => setIsOpen(false)}
          style={{
            position: 'fixed',
            top: 0, left: 0,
            width: '100vw', height: '100vh',
            zIndex: 150,
          }}
        />
      )}
    </div>
  );
}

export default MultiSelectDropdown;
