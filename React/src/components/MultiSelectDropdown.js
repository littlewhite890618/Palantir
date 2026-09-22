import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

// 機關、金額和期限的多選下拉選單元件，因為三個元件功能相同，所以共同一個元件
//傳進來的參數為Props: label、options、selectedValues、onChange
function MultiSelectDropdown({ label, options, selectedValues, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const hasSelection = selectedValues.length > 0;

  //切換某個選項的勾選狀態
  const toggleOption = (option) => {
    if (selectedValues.includes(option)) {
      onChange(selectedValues.filter((v) => v !== option));
    } else {
      onChange([...selectedValues, option]);
    }
  };

  //篩選器選擇的數量，若有選擇則顯示ex:機關(2)，否則顯示ex:機關
  const buttonLabel = hasSelection
    ? `${label}（${selectedValues.length}）`
    : label;

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '7px 12px',
          border: `1px solid ${hasSelection ? '#1a73e8' : '#e5e7eb'}`,
          borderRadius: '8px',
          background: hasSelection ? '#eaf1fd' : '#fff',
          color: hasSelection ? '#1a73e8' : '#374151',
          fontSize: '13px',
          cursor: 'pointer',
        }}
      >
        {buttonLabel}
        <ChevronDown size={14} strokeWidth={2} />
      </button>
      {/* 展開後的選項清單 */}
      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '40px',
          left: 0,
          minWidth: '200px',
          maxHeight: '320px',
          overflowY: 'auto',
          background: 'white',
          borderRadius: '10px',
          boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
          border: '1px solid #eef0f2',
          zIndex: 200,
          padding: '6px 0',
        }}>
          {options.map((option) => (
            <label
              key={option}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 14px',
                cursor: 'pointer',
                fontSize: '14px',
                color: '#374151',
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
