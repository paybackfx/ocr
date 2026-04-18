import React from 'react';

export default function Header() {
  return (
    <header className="bg-gradient-to-br from-[#0a1628] to-[#0f2847] border-b-[3px] border-cyan-400 px-8 py-5 flex items-center justify-between rounded-b-2xl mb-8 shadow-[0_4px_30px_rgba(0,200,255,0.15)]">
      <div className="flex items-center gap-4">
        <svg width="44" height="44" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="50" cy="50" r="45" fill="none" stroke="#00D4FF" strokeWidth="4" />
          <path d="M30 60 Q50 20 70 60" stroke="#00D4FF" strokeWidth="5" fill="none" strokeLinecap="round" />
          <circle cx="50" cy="38" r="6" fill="#00D4FF" />
        </svg>
        <div>
          <div className="text-2xl font-extrabold text-white tracking-widest leading-none">
            ONWAVE
          </div>
          <div className="text-xs font-normal text-cyan-300 tracking-[0.15em] uppercase mt-1">
            Document Processing & Reconciliation
          </div>
        </div>
      </div>
      <div className="bg-gradient-to-br from-cyan-500 to-blue-600 text-white px-4 py-1.5 rounded-full text-sm font-semibold tracking-wide">
        🌊 SaaS Fiduciaire
      </div>
    </header>
  );
}
