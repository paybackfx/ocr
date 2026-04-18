import React from 'react';

export default function Header() {
  return (
    <header className="bg-gradient-to-br from-[#0d1f45] to-[#122055] border-b-[3px] border-imtiaz-pink px-8 py-5 flex items-center justify-between rounded-b-2xl mb-8 shadow-[0_4px_30px_rgba(233,30,140,0.2)]">
      <div className="flex items-center gap-4">
        <svg width="44" height="44" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="0" y="20" width="44" height="44" fill="#E91E8C" rx="4" />
          <rect x="36" y="0" width="44" height="44" fill="#5BC8F5" rx="4" />
          <rect x="18" y="55" width="28" height="28" fill="#8DC63F" rx="4" />
        </svg>
        <div>
          <div className="text-2xl font-extrabold text-white tracking-widest leading-none">
            IMTIAZ TAAMINE
          </div>
          <div className="text-xs font-normal text-imtiaz-blue tracking-[0.15em] uppercase mt-1">
            Extraction Intelligente de Documents
          </div>
        </div>
      </div>
      <div className="bg-gradient-to-br from-imtiaz-pink to-[#c0186c] text-white px-4 py-1.5 rounded-full text-sm font-semibold tracking-wide">
        🦅 OCR Propulsé par IA
      </div>
    </header>
  );
}
