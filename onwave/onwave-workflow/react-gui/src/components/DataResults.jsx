import React, { useState } from 'react';
import { Copy, Check, ChevronDown } from 'lucide-react';

const CopyButton = ({ text, className = "ml-2 text-imtiaz-textMuted hover:text-white transition-colors" }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    if (!text) return;
    navigator.clipboard.writeText(String(text));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={handleCopy} className={className} title="Copier">
      {copied ? <Check size={14} className="text-imtiaz-green" /> : <Copy size={14} />}
    </button>
  );
};

/* ─── Labels for facture fields ─────────────────────── */
const factureLabels = {
  fournisseur: "Fournisseur",
  numero_facture: "N° Facture",
  date_facture: "Date Facture",
  date_echeance: "Date Échéance",
  ice: "ICE",
  identifiant_fiscal: "IF",
  montant_ht: "Montant HT",
  taux_tva: "Taux TVA (%)",
  montant_tva: "Montant TVA",
  montant_ttc: "Montant TTC",
  devise: "Devise",
  mode_paiement: "Mode Paiement",
  description: "Description",
};

const releveLabels = {
  banque: "Banque",
  numero_compte: "N° Compte",
  titulaire: "Titulaire",
  periode_du: "Période du",
  periode_au: "Période au",
  solde_initial: "Solde Initial",
  solde_final: "Solde Final",
  devise: "Devise",
};

/* ─── Amount formatter ─────────────────────── */
function fmtAmount(val) {
  if (val === null || val === undefined || val === '' || val === 'NULL') return null;
  const n = Number(val);
  if (isNaN(n)) return String(val);
  return n.toLocaleString('fr-MA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' MAD';
}

const amountFields = ['montant_ht', 'montant_tva', 'montant_ttc', 'solde_initial', 'solde_final'];

/* ─── Facture Card ──────────────────────────── */
function FactureCard({ facture }) {
  if (!facture) return null;
  return (
    <div className="mb-6">
      <h4 className="font-bold text-imtiaz-blue text-[0.95rem] mb-3 tracking-widest uppercase flex items-center gap-2">
        🧾 FACTURE
      </h4>
      <div className="space-y-0.5">
        {Object.entries(factureLabels).map(([key, label]) => {
          const raw = facture[key];
          const isNull = raw === null || raw === undefined || raw === '' || raw === 'NULL' || raw === '-';
          const display = amountFields.includes(key) ? fmtAmount(raw) : raw;
          
          return (
            <div key={key} className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
              <span className="text-imtiaz-textMutedDark text-[0.78rem] font-semibold uppercase tracking-wider flex-1">
                {label}
              </span>
              <span className="flex-1 flex items-center justify-end">
                {!isNull && display ? (
                  <div className="flex items-center">
                    <code className={`px-2 py-1 rounded font-mono text-sm inline-block ${
                      amountFields.includes(key) 
                        ? 'bg-imtiaz-green/10 text-imtiaz-green font-bold' 
                        : 'bg-white/5 text-[#e8f0ff]'
                    }`}>
                      {key === 'taux_tva' ? `${raw}%` : display}
                    </code>
                    <CopyButton text={String(raw)} />
                  </div>
                ) : (
                  <span className="text-imtiaz-pink font-semibold text-sm">—</span>
                )}
              </span>
            </div>
          );
        })}
      </div>

      {/* Math verification badge */}
      {facture.montant_ht && facture.montant_tva && facture.montant_ttc && (
        <div className="mt-3">
          {(() => {
            const ht = Number(facture.montant_ht);
            const tva = Number(facture.montant_tva);
            const ttc = Number(facture.montant_ttc);
            const calc = ht + tva;
            const diff = Math.abs(calc - ttc);
            const ok = diff < 0.02; // tolerance 2 centimes
            return (
              <div className={`flex items-center gap-2 text-xs font-semibold px-3 py-2 rounded-lg ${
                ok ? 'bg-imtiaz-green/10 text-imtiaz-green' : 'bg-imtiaz-pink/10 text-imtiaz-pink'
              }`}>
                {ok ? '✅' : '⚠️'} Vérification: HT ({ht.toFixed(2)}) + TVA ({tva.toFixed(2)}) = {calc.toFixed(2)}
                {ok ? ' ✓ Correspond au TTC' : ` ≠ TTC (${ttc.toFixed(2)}) — Différence: ${diff.toFixed(2)}`}
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}

/* ─── Relevé Bancaire Card ──────────────────── */
function ReleveCard({ releve }) {
  if (!releve) return null;
  const transactions = releve.transactions || [];
  
  return (
    <div className="mb-6">
      <h4 className="font-bold text-cyan-400 text-[0.95rem] mb-3 tracking-widest uppercase flex items-center gap-2">
        🏦 RELEVÉ BANCAIRE
      </h4>
      
      {/* Header info */}
      <div className="space-y-0.5 mb-4">
        {Object.entries(releveLabels).map(([key, label]) => {
          const raw = releve[key];
          const isNull = raw === null || raw === undefined || raw === '' || raw === 'NULL' || raw === '-';
          const display = amountFields.includes(key) ? fmtAmount(raw) : raw;
          
          return (
            <div key={key} className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
              <span className="text-imtiaz-textMutedDark text-[0.78rem] font-semibold uppercase tracking-wider flex-1">
                {label}
              </span>
              <span className="flex-1 flex items-center justify-end">
                {!isNull && display ? (
                  <div className="flex items-center">
                    <code className={`px-2 py-1 rounded font-mono text-sm inline-block ${
                      amountFields.includes(key) ? 'bg-cyan-400/10 text-cyan-400 font-bold' : 'bg-white/5 text-[#e8f0ff]'
                    }`}>
                      {display}
                    </code>
                    <CopyButton text={String(raw)} />
                  </div>
                ) : (
                  <span className="text-imtiaz-pink font-semibold text-sm">—</span>
                )}
              </span>
            </div>
          );
        })}
      </div>
      
      {/* Transactions table */}
      {transactions.length > 0 && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <h5 className="text-white/70 text-xs font-bold uppercase tracking-widest">
              💳 Transactions ({transactions.length} lignes)
            </h5>
            <CopyButton 
              text={transactions.map(tx => 
                `${tx.date || ''}\t${tx.libelle || ''}\t${tx.debit || ''}\t${tx.credit || ''}\t${tx.solde || ''}`
              ).join('\n')}
              className="text-imtiaz-textMuted hover:text-white transition-colors"
            />
          </div>
          <div className="overflow-x-auto rounded-xl border border-white/5">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-white/5 text-imtiaz-textMuted uppercase tracking-wider">
                  <th className="text-left py-2.5 px-3 font-semibold">#</th>
                  <th className="text-left py-2.5 px-3 font-semibold">Date</th>
                  <th className="text-left py-2.5 px-3 font-semibold min-w-[200px]">Libellé</th>
                  <th className="text-right py-2.5 px-3 font-semibold">Débit</th>
                  <th className="text-right py-2.5 px-3 font-semibold">Crédit</th>
                  <th className="text-right py-2.5 px-3 font-semibold">Solde</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx, i) => (
                  <tr key={i} className="border-t border-white/5 hover:bg-white/[0.03] transition-colors">
                    <td className="py-2 px-3 text-imtiaz-textMutedDark">{i + 1}</td>
                    <td className="py-2 px-3 text-white/80 font-mono whitespace-nowrap">{tx.date || '—'}</td>
                    <td className="py-2 px-3 text-white/90 max-w-[300px]">{tx.libelle || '—'}</td>
                    <td className="py-2 px-3 text-right font-mono whitespace-nowrap">
                      {tx.debit ? (
                        <span className="text-imtiaz-pink font-semibold">-{Number(tx.debit).toLocaleString('fr-MA', {minimumFractionDigits: 2})} </span>
                      ) : ''}
                    </td>
                    <td className="py-2 px-3 text-right font-mono whitespace-nowrap">
                      {tx.credit ? (
                        <span className="text-imtiaz-green font-semibold">+{Number(tx.credit).toLocaleString('fr-MA', {minimumFractionDigits: 2})}</span>
                      ) : ''}
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-white/60 whitespace-nowrap">
                      {tx.solde != null ? Number(tx.solde).toLocaleString('fr-MA', {minimumFractionDigits: 2}) : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
              {/* Totals row */}
              <tfoot>
                <tr className="border-t-2 border-white/10 bg-white/[0.03] font-bold">
                  <td colSpan={3} className="py-2.5 px-3 text-white/50 uppercase text-[0.7rem] tracking-widest">Totaux</td>
                  <td className="py-2.5 px-3 text-right font-mono text-imtiaz-pink">
                    {transactions.filter(t => t.debit).reduce((s, t) => s + Number(t.debit || 0), 0).toLocaleString('fr-MA', {minimumFractionDigits: 2})}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-imtiaz-green">
                    {transactions.filter(t => t.credit).reduce((s, t) => s + Number(t.credit || 0), 0).toLocaleString('fr-MA', {minimumFractionDigits: 2})}
                  </td>
                  <td className="py-2.5 px-3"></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── CoT Analysis Card ──────────────────────── */
function CoTCard({ analyse, validation }) {
  if (!analyse && !validation) return null;
  return (
    <details className="group mb-4">
      <summary className="flex items-center gap-2 cursor-pointer text-amber-400/70 text-xs uppercase tracking-wider font-semibold hover:text-amber-400 transition-colors select-none">
        🧠 Analyse Double-Check (CoT) <ChevronDown size={14} className="group-open:rotate-180 transition-transform" />
      </summary>
      <div className="mt-3 space-y-3">
        {analyse && (
          <div className="bg-amber-400/5 border border-amber-400/15 p-4 rounded-xl">
            <p className="text-amber-400/60 text-[0.65rem] uppercase tracking-widest font-bold mb-1">Analyse des Montants</p>
            <pre className="text-white/70 font-mono text-xs whitespace-pre-wrap">{analyse}</pre>
          </div>
        )}
        {validation && (
          <div className="bg-imtiaz-green/5 border border-imtiaz-green/15 p-4 rounded-xl">
            <p className="text-imtiaz-green/60 text-[0.65rem] uppercase tracking-widest font-bold mb-1">Validation Critique</p>
            <pre className="text-white/70 font-mono text-xs whitespace-pre-wrap">{validation}</pre>
          </div>
        )}
      </div>
    </details>
  );
}

/* ─── Main Component ──────────────────────────── */
export default function DataResults({ results }) {
  if (!results || results.length === 0) return null;

  return (
    <div className="w-full max-w-5xl mx-auto my-8 space-y-6">
      <div className="bg-imtiaz-green/10 border border-imtiaz-green/40 text-imtiaz-green rounded-xl py-3.5 px-6 text-center font-semibold text-sm">
        ✅ Extraction terminée avec succès !
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-imtiaz-card/80 border border-imtiaz-blue/15 rounded-xl p-4">
          <p className="text-imtiaz-textMuted text-xs mb-1">📁 Fichiers</p>
          <p className="text-white font-bold text-xl">{results[0]?.filenames?.length || 0}</p>
        </div>
        <div className="bg-imtiaz-card/80 border border-imtiaz-blue/15 rounded-xl p-4">
          <p className="text-imtiaz-textMuted text-xs mb-1">📊 Type Document</p>
          <p className="text-cyan-400 font-bold text-sm mt-1">{results[0]?.type_document || results[0]?.extracted_data?.type_document || '—'}</p>
        </div>
      </div>

      {results.map((resItem, docIdx) => {
        const extracted = resItem.extracted_data || resItem;
        const facture = extracted.facture || null;
        const releve = extracted.releve_bancaire || null;
        const analyseCoT = extracted.analyse_montants || '';
        const validationCoT = extracted.validation_critique || '';

        if (!facture && !releve) return null;

        return (
          <div key={docIdx} className="bg-imtiaz-card border-t-[3px] border-cyan-400/30 shadow-lg rounded-2xl p-6 mt-4">
            <h3 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
              🌊 Document {docIdx + 1}
            </h3>

            {/* Chain of Thought Analysis */}
            <CoTCard analyse={analyseCoT} validation={validationCoT} />

            {/* Facture Section */}
            <FactureCard facture={facture} />

            {/* Relevé Bancaire Section */}
            <ReleveCard releve={releve} />

            {/* Text Report */}
            {resItem.txt_report && (
              <div className="mt-6 border-t border-white/5 pt-4">
                <details className="group">
                  <summary className="flex items-center gap-2 cursor-pointer text-imtiaz-textMuted text-xs uppercase tracking-wider font-semibold hover:text-white transition-colors select-none">
                    📝 Rapport texte <ChevronDown size={14} className="group-open:rotate-180 transition-transform" />
                  </summary>
                  <div className="mt-3 bg-black/40 border border-white/5 p-4 rounded-xl relative">
                     <div className="absolute top-3 right-3">
                       <CopyButton text={resItem.txt_report} />
                     </div>
                     <pre className="text-white/70 font-mono text-xs whitespace-pre-wrap">{resItem.txt_report}</pre>
                  </div>
                </details>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
