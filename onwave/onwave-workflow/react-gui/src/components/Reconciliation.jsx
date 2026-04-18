import React, { useState } from 'react';
import { Loader2, CheckCircle, AlertTriangle, XCircle, ChevronDown, Download, Shield, ShieldAlert, Layers, PieChart } from 'lucide-react';

function fmtAmount(val) {
  if (val === null || val === undefined) return '—';
  const n = Number(val);
  if (isNaN(n)) return String(val);
  return n.toLocaleString('fr-MA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' MAD';
}

/* ─── CSV / XML Export helpers ─── */
function downloadFile(content, filename, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function toCsv(headers, rows) {
  const escape = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const lines = [headers.map(escape).join(';')];
  rows.forEach((r) => lines.push(r.map(escape).join(';')));
  return '\uFEFF' + lines.join('\r\n'); // BOM for Excel FR
}

function toXml(rootTag, rowTag, headers, rows) {
  let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
  xml += `<${rootTag}>\n`;
  rows.forEach((r) => {
    xml += `  <${rowTag}>\n`;
    headers.forEach((h, i) => {
      const tag = h.replace(/[^a-zA-Z0-9_]/g, '_');
      xml += `    <${tag}>${String(r[i] ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;')}</${tag}>\n`;
    });
    xml += `  </${rowTag}>\n`;
  });
  xml += `</${rootTag}>`;
  return xml;
}

function buildAchatsRows(data) {
  const headers = ['Journal', 'Date', 'Piece', 'Compte', 'Libelle', 'Debit', 'Credit'];
  const rows = [];
  const sources = [...(data.matched || []), ...(data.partial || [])];
  sources.forEach((pair) => {
    (pair.ecritures_comptables || []).forEach((ec) => {
      if (ec.journal !== 'HA') return;
      (ec.lignes || []).forEach((l) => {
        rows.push([ec.journal, ec.date, ec.piece, l.compte, l.libelle, l.debit || '', l.credit || '']);
      });
    });
  });
  return { headers, rows };
}

function buildBanqueRows(data) {
  const headers = ['Journal', 'Date', 'Piece', 'Compte', 'Libelle', 'Debit', 'Credit'];
  const rows = [];
  const sources = [...(data.matched || []), ...(data.partial || [])];
  sources.forEach((pair) => {
    (pair.ecritures_comptables || []).forEach((ec) => {
      if (ec.journal !== 'BQ') return;
      (ec.lignes || []).forEach((l) => {
        rows.push([ec.journal, ec.date, ec.piece, l.compte, l.libelle, l.debit || '', l.credit || '']);
      });
    });
  });
  return { headers, rows };
}

function buildRapprochementRows(data) {
  const headers = [
    'Match', 'Confidence', 'Score', 'Fournisseur', 'Date_Facture', 'Montant_HT', 'Montant_TVA', 'Montant_TTC',
    'Date_Banque', 'Libelle_Banque', 'Debit', 'Credit', 'Ecart_Jours',
  ];
  const rows = [];
  const sources = [...(data.matched || []), ...(data.partial || [])];
  sources.forEach((pair) => {
    const inv = pair.invoice;
    const bank = pair.bank_transaction;
    rows.push([
      pair.match_type, pair.confidence, pair.score,
      inv.Fournisseur, inv.Date,
      inv.Montant_HT, inv.Montant_TVA, inv.Montant_TTC,
      bank.Date, bank.Libelle, bank.Debit || '', bank.Credit || '',
      pair.day_gap,
    ]);
  });
  return { headers, rows };
}

/* ─── Badge match type ─── */
function MatchBadge({ type }) {
  const styles = {
    EXACT: 'bg-imtiaz-green/15 text-imtiaz-green border-imtiaz-green/30',
    NEAR: 'bg-amber-400/15 text-amber-400 border-amber-400/30',
    PARTIAL: 'bg-orange-400/15 text-orange-400 border-orange-400/30',
    GROUPED: 'bg-violet-400/15 text-violet-400 border-violet-400/30',
  };
  const icons = {
    EXACT: '✓',
    NEAR: '≈',
    PARTIAL: '½',
    GROUPED: '⊕',
  };
  return (
    <span className={`text-[0.65rem] uppercase tracking-widest font-bold px-2.5 py-1 rounded-full border inline-flex items-center gap-1 ${styles[type] || 'bg-white/10 text-white/60 border-white/20'}`}>
      <span>{icons[type] || '?'}</span> {type}
    </span>
  );
}

/* ─── Confidence badge (auto / suggestion) ─── */
function ConfidenceBadge({ confidence }) {
  if (confidence === 'auto') {
    return (
      <span className="text-[0.6rem] uppercase tracking-widest font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 inline-flex items-center gap-1">
        <Shield size={10} /> AUTO
      </span>
    );
  }
  return (
    <span className="text-[0.6rem] uppercase tracking-widest font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/25 inline-flex items-center gap-1">
      <ShieldAlert size={10} /> REVUE
    </span>
  );
}

/* ─── Score bar (visual gauge) ─── */
function ScoreBar({ score, label, color = 'bg-imtiaz-green' }) {
  const pct = Math.round((score || 0) * 100);
  const barColor =
    pct >= 80 ? 'bg-emerald-400' :
    pct >= 50 ? 'bg-amber-400' :
    'bg-red-400';
  return (
    <div className="flex items-center gap-2">
      {label && <span className="text-imtiaz-textMutedDark text-[0.65rem] w-16 text-right font-semibold uppercase tracking-wider">{label}</span>}
      <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color || barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-bold font-mono w-10 text-right ${pct >= 80 ? 'text-emerald-400' : pct >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
        {pct}%
      </span>
    </div>
  );
}

/* ─── Score Details breakdown ─── */
function ScoreDetails({ details, matchType }) {
  if (!details) return null;

  // Partial match details
  if (matchType === 'PARTIAL') {
    return (
      <div className="bg-orange-400/5 border border-orange-400/10 rounded-lg p-3 space-y-2">
        <p className="text-orange-400/80 text-[0.6rem] uppercase tracking-widest font-bold mb-2">Détails Acompte</p>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <div className="flex justify-between">
            <span className="text-imtiaz-textMutedDark">Payé</span>
            <span className="text-orange-400 font-bold font-mono">{fmtAmount(details.amount_paid)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-imtiaz-textMutedDark">Dû (TTC)</span>
            <span className="text-white/80 font-mono">{fmtAmount(details.amount_due)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-imtiaz-textMutedDark">% Réglé</span>
            <span className="text-orange-400 font-bold font-mono">{details.pct_paid}%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-imtiaz-textMutedDark">Résiduel</span>
            <span className="text-imtiaz-pink font-bold font-mono">{fmtAmount(details.amount_residual)}</span>
          </div>
        </div>
        {details.label_score != null && (
          <ScoreBar score={details.label_score} label="Label" color="bg-orange-400" />
        )}
      </div>
    );
  }

  // Grouped match details
  if (matchType === 'GROUPED') {
    return (
      <div className="bg-violet-400/5 border border-violet-400/10 rounded-lg p-3 space-y-2">
        <p className="text-violet-400/80 text-[0.6rem] uppercase tracking-widest font-bold mb-2 flex items-center gap-1">
          <Layers size={12} /> Paiement Groupé
        </p>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <div className="flex justify-between">
            <span className="text-imtiaz-textMutedDark">Factures</span>
            <span className="text-violet-400 font-bold font-mono">{details.invoices_count}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-imtiaz-textMutedDark">Total Factures</span>
            <span className="text-violet-400 font-bold font-mono">{fmtAmount(details.invoices_total)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-imtiaz-textMutedDark">Écart</span>
            <span className="text-white/80 font-mono">{fmtAmount(details.amount_diff)}</span>
          </div>
        </div>
        {details.label_score != null && (
          <ScoreBar score={details.label_score} label="Label" color="bg-violet-400" />
        )}
      </div>
    );
  }

  // EXACT / NEAR — full score breakdown
  return (
    <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3 space-y-1.5">
      <p className="text-white/40 text-[0.6rem] uppercase tracking-widest font-bold mb-2 flex items-center gap-1">
        <PieChart size={11} /> Décomposition du Score
      </p>
      <ScoreBar score={details.amount_score} label="Montant" color="bg-emerald-400" />
      <ScoreBar score={details.label_score} label="Label" color="bg-sky-400" />
      <ScoreBar score={details.date_score} label="Date" color="bg-amber-400" />
      <ScoreBar score={details.ref_score} label="Réf" color="bg-violet-400" />
      {details.amount_diff != null && (
        <div className="flex items-center gap-2 mt-1.5 pt-1.5 border-t border-white/5">
          <span className="text-imtiaz-textMutedDark text-[0.65rem] font-semibold">Écart montant:</span>
          <span className={`text-xs font-bold font-mono ${details.amount_diff <= 0.05 ? 'text-emerald-400' : 'text-amber-400'}`}>
            {details.amount_diff.toFixed(2)} MAD
          </span>
        </div>
      )}
    </div>
  );
}

/* ─── Matched pair row ─── */
function MatchedRow({ pair, index }) {
  const [open, setOpen] = useState(false);
  const inv = pair.invoice;
  const bank = pair.bank_transaction;
  const ecritures = pair.ecritures_comptables || [];
  const isGrouped = pair.match_type === 'GROUPED';
  const groupedInvoices = pair.invoices || [inv];
  const scorePct = Math.round((pair.score || 0) * 100);

  return (
    <div className={`bg-imtiaz-card/80 border rounded-xl overflow-hidden ${
      pair.match_type === 'PARTIAL' ? 'border-orange-400/20' :
      pair.match_type === 'GROUPED' ? 'border-violet-400/20' :
      'border-imtiaz-green/20'
    }`}>
      {/* Summary row */}
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-white/[0.03] transition-colors"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-4 flex-1 min-w-0">
          <span className="text-white/40 text-xs font-mono w-6">#{index + 1}</span>
          <div className="flex-1 min-w-0">
            <p className="text-white font-semibold text-sm truncate">
              {isGrouped
                ? `${groupedInvoices.length} factures → ${bank.Libelle || 'Mouvement bancaire'}`
                : (inv.Fournisseur || inv.fournisseur || 'Fournisseur')
              }
            </p>
            <p className="text-imtiaz-textMuted text-xs mt-0.5">
              Facture: {inv.Date} &rarr; Banque: {bank.Date} ({pair.day_gap}j)
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Score pill */}
          <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded-md ${
            scorePct >= 80 ? 'bg-emerald-500/15 text-emerald-400' :
            scorePct >= 50 ? 'bg-amber-400/15 text-amber-400' :
            'bg-red-400/15 text-red-400'
          }`}>
            {scorePct}%
          </span>
          <ConfidenceBadge confidence={pair.confidence} />
          <span className="text-imtiaz-green font-bold font-mono text-sm">{fmtAmount(inv.Montant_TTC)}</span>
          <MatchBadge type={pair.match_type} />
          <ChevronDown size={16} className={`text-white/40 transition-transform ${open ? 'rotate-180' : ''}`} />
        </div>
      </div>

      {/* Detail panel */}
      {open && (
        <div className="border-t border-white/5 px-5 py-4 space-y-4">
          {/* Overall Score Bar */}
          <div className="bg-white/[0.02] rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white/50 text-[0.6rem] uppercase tracking-widest font-bold">Score Global</span>
              <div className="flex items-center gap-2">
                <ConfidenceBadge confidence={pair.confidence} />
                <span className={`text-sm font-bold font-mono ${
                  scorePct >= 80 ? 'text-emerald-400' : scorePct >= 50 ? 'text-amber-400' : 'text-red-400'
                }`}>
                  {pair.score?.toFixed(4)} ({scorePct}%)
                </span>
              </div>
            </div>
            <div className="w-full h-2.5 bg-white/5 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ${
                  scorePct >= 80 ? 'bg-gradient-to-r from-emerald-500 to-emerald-400' :
                  scorePct >= 50 ? 'bg-gradient-to-r from-amber-500 to-amber-400' :
                  'bg-gradient-to-r from-red-500 to-red-400'
                }`}
                style={{ width: `${scorePct}%` }}
              />
            </div>
          </div>

          {/* Score Details */}
          <ScoreDetails details={pair.score_details} matchType={pair.match_type} />

          {/* Grouped: list all invoices */}
          {isGrouped && groupedInvoices.length > 1 && (
            <div>
              <p className="text-violet-400/80 text-[0.65rem] uppercase tracking-widest font-bold mb-2">
                Factures Regroupées ({groupedInvoices.length})
              </p>
              <div className="space-y-2">
                {groupedInvoices.map((gInv, gi) => (
                  <div key={gi} className="bg-violet-400/5 border border-violet-400/10 rounded-lg p-3 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-violet-400/50 text-xs font-mono">#{gi + 1}</span>
                      <div>
                        <p className="text-white/90 text-sm font-semibold">{gInv.Fournisseur}</p>
                        <p className="text-imtiaz-textMuted text-xs">{gInv.Date} · N° {gInv.Numero_Facture || '—'}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-violet-400 font-bold font-mono text-sm">{fmtAmount(gInv.Montant_TTC)}</p>
                      <p className="text-imtiaz-textMuted text-[0.65rem]">HT: {fmtAmount(gInv.Montant_HT)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Invoice vs Bank side by side */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white/[0.03] rounded-lg p-3">
              <p className="text-imtiaz-blue text-[0.65rem] uppercase tracking-widest font-bold mb-2">Facture</p>
              <div className="space-y-1 text-xs">
                <Row label="Fournisseur" value={inv.Fournisseur} />
                <Row label="Date" value={inv.Date} />
                <Row label="HT" value={fmtAmount(inv.Montant_HT)} />
                <Row label="TVA" value={fmtAmount(inv.Montant_TVA)} />
                <Row label="TTC" value={fmtAmount(inv.Montant_TTC)} highlight />
                {inv.ICE && <Row label="ICE" value={inv.ICE} />}
                {inv.Numero_Facture && <Row label="N° Facture" value={inv.Numero_Facture} />}
              </div>
            </div>
            <div className="bg-white/[0.03] rounded-lg p-3">
              <p className="text-cyan-400 text-[0.65rem] uppercase tracking-widest font-bold mb-2">Mouvement bancaire</p>
              <div className="space-y-1 text-xs">
                <Row label="Date" value={bank.Date} />
                <Row label="Libelle" value={bank.Libelle} />
                <Row label="Debit" value={fmtAmount(bank.Debit)} highlight={bank.Debit > 0} />
                <Row label="Credit" value={fmtAmount(bank.Credit)} highlight={bank.Credit > 0} />
              </div>
            </div>
          </div>

          {/* PCGM Ecritures */}
          {ecritures.length > 0 && (
            <div>
              <p className="text-amber-400/80 text-[0.65rem] uppercase tracking-widest font-bold mb-2">Ecritures PCGM</p>
              <div className="overflow-x-auto rounded-lg border border-white/5">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-white/5 text-imtiaz-textMuted uppercase tracking-wider">
                      <th className="text-left py-2 px-3 font-semibold">Journal</th>
                      <th className="text-left py-2 px-3 font-semibold">Date</th>
                      <th className="text-left py-2 px-3 font-semibold">Compte</th>
                      <th className="text-left py-2 px-3 font-semibold">Libelle</th>
                      <th className="text-right py-2 px-3 font-semibold">Debit</th>
                      <th className="text-right py-2 px-3 font-semibold">Credit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ecritures.map((ec, ei) =>
                      ec.lignes?.map((l, li) => (
                        <tr key={`${ei}-${li}`} className="border-t border-white/5">
                          {li === 0 && (
                            <>
                              <td rowSpan={ec.lignes.length} className="py-2 px-3 font-mono font-bold text-white/70">{ec.journal}</td>
                              <td rowSpan={ec.lignes.length} className="py-2 px-3 text-white/60 whitespace-nowrap">{ec.date}</td>
                            </>
                          )}
                          <td className="py-2 px-3 font-mono text-imtiaz-blue">{l.compte}</td>
                          <td className="py-2 px-3 text-white/80">{l.libelle}</td>
                          <td className="py-2 px-3 text-right font-mono">
                            {l.debit > 0 ? <span className="text-imtiaz-pink">{fmtAmount(l.debit)}</span> : ''}
                          </td>
                          <td className="py-2 px-3 text-right font-mono">
                            {l.credit > 0 ? <span className="text-imtiaz-green">{fmtAmount(l.credit)}</span> : ''}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Row({ label, value, highlight }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-imtiaz-textMutedDark">{label}</span>
      <span className={highlight ? 'text-imtiaz-green font-bold font-mono' : 'text-white/80'}>{value || '—'}</span>
    </div>
  );
}

/* ─── Unmatched list ─── */
function UnmatchedSection({ title, icon, items, color, fields }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <h4 className={`font-bold text-sm mb-3 flex items-center gap-2 ${color}`}>
        {icon} {title} ({items.length})
      </h4>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="bg-imtiaz-card/60 border border-imtiaz-pink/15 rounded-lg px-4 py-3 flex items-center justify-between text-xs">
            <div className="flex items-center gap-3">
              <span className="text-white/40 font-mono">#{i + 1}</span>
              {fields.map((f) => (
                <span key={f} className="text-white/70">
                  {item[f] || ''}
                </span>
              ))}
            </div>
            <span className="text-imtiaz-pink font-bold font-mono">
              {fmtAmount(item.Montant_TTC || item.Debit || item.Credit)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Main component ─── */
export default function Reconciliation({ results }) {
  const [reconcileData, setReconcileData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Extract factures and releve from results
  const allFactures = [];
  const allBankLines = [];

  (results || []).forEach((resItem) => {
    const extracted = resItem.extracted_data || resItem;
    const facture = extracted.facture || null;
    const releve = extracted.releve_bancaire || null;

    if (facture) {
      allFactures.push({
        Date: facture.date_facture || '',
        Fournisseur: facture.fournisseur || 'FOURNISSEUR INCONNU',
        ICE: facture.ice || '',
        Numero_Facture: facture.numero_facture || '',
        Montant_HT: Number(facture.montant_ht) || 0,
        Montant_TVA: Number(facture.montant_tva) || 0,
        Montant_TTC: Number(facture.montant_ttc) || 0,
      });
    }

    if (releve?.transactions) {
      releve.transactions.forEach((tx) => {
        allBankLines.push({
          Date: tx.date || '',
          Libelle: tx.libelle || '',
          Debit: Number(tx.debit) || 0,
          Credit: Number(tx.credit) || 0,
        });
      });
    }
  });

  const hasFactures = allFactures.length > 0;
  const hasBankLines = allBankLines.length > 0;
  const canReconcile = hasFactures && hasBankLines;

  if (!hasFactures && !hasBankLines) return null;

  const handleReconcile = async () => {
    setLoading(true);
    setError(null);
    setReconcileData(null);

    try {
      const res = await fetch('/api/v1/reconcile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          invoices: allFactures,
          bank_statements: allBankLines,
          tolerance_mad: 0.50,
          max_day_gap: 90,
          allow_partial: true,
          allow_grouped: true,
        }),
      });

      if (!res.ok) throw new Error(`Erreur serveur: ${res.status}`);
      const data = await res.json();
      setReconcileData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto my-8 space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-[#0d1f45] to-[#0a1628] border border-cyan-400/20 rounded-2xl p-6">
        <h3 className="text-white font-bold text-lg mb-2 flex items-center gap-2">
          Rapprochement Bancaire
        </h3>
        <p className="text-imtiaz-textMuted text-sm mb-4">
          Matching automatique factures / releve bancaire avec generation d'ecritures PCGM.
        </p>

        {/* Status badges */}
        <div className="flex items-center gap-3 mb-5">
          <span className={`text-xs font-semibold px-3 py-1.5 rounded-full border ${hasFactures ? 'bg-imtiaz-green/10 text-imtiaz-green border-imtiaz-green/30' : 'bg-white/5 text-imtiaz-textMuted border-white/10'}`}>
            {hasFactures ? <CheckCircle size={12} className="inline mr-1" /> : <XCircle size={12} className="inline mr-1" />}
            {allFactures.length} facture{allFactures.length > 1 ? 's' : ''}
          </span>
          <span className={`text-xs font-semibold px-3 py-1.5 rounded-full border ${hasBankLines ? 'bg-cyan-400/10 text-cyan-400 border-cyan-400/30' : 'bg-white/5 text-imtiaz-textMuted border-white/10'}`}>
            {hasBankLines ? <CheckCircle size={12} className="inline mr-1" /> : <XCircle size={12} className="inline mr-1" />}
            {allBankLines.length} ligne{allBankLines.length > 1 ? 's' : ''} bancaire{allBankLines.length > 1 ? 's' : ''}
          </span>
        </div>

        {!canReconcile && (
          <div className="bg-amber-400/10 border border-amber-400/30 text-amber-400 rounded-xl py-3 px-5 text-sm font-semibold">
            <AlertTriangle size={14} className="inline mr-2" />
            {!hasFactures
              ? 'Aucune facture detectee. Uploadez une facture + un releve pour lancer le rapprochement.'
              : 'Aucun releve bancaire detecte. Uploadez un releve + une facture pour lancer le rapprochement.'}
          </div>
        )}

        {canReconcile && !reconcileData && (
          <button
            onClick={handleReconcile}
            disabled={loading}
            className="w-full bg-gradient-to-br from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white border-0 rounded-xl py-3.5 px-8 font-bold text-base tracking-wide uppercase shadow-[0_4px_20px_rgba(0,200,255,0.3)] hover:shadow-[0_6px_30px_rgba(0,200,255,0.5)] hover:-translate-y-0.5 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin w-5 h-5" />
                Rapprochement en cours...
              </>
            ) : (
              'Lancer le Rapprochement Bancaire'
            )}
          </button>
        )}
      </div>

      {error && (
        <div className="bg-imtiaz-pink/10 border border-imtiaz-pink/40 text-imtiaz-pink rounded-xl py-3.5 px-6 text-center font-semibold text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {reconcileData && (
        <div className="space-y-6">
          {/* Summary — 2 rows of cards */}
          <div className="grid grid-cols-4 gap-3">
            <SummaryCard label="Rapprochés" value={reconcileData.summary?.matched_count} color="text-imtiaz-green" bg="bg-imtiaz-green/10 border-imtiaz-green/20" />
            <SummaryCard label="Auto-réconciliés" value={reconcileData.summary?.auto_reconciled} color="text-emerald-400" bg="bg-emerald-400/10 border-emerald-400/20" icon={<Shield size={14} />} />
            <SummaryCard label="À revoir" value={reconcileData.summary?.suggestions} color="text-amber-400" bg="bg-amber-400/10 border-amber-400/20" icon={<ShieldAlert size={14} />} />
            <SummaryCard label="Écritures PCGM" value={reconcileData.summary?.ecritures_generated} color="text-imtiaz-blue" bg="bg-imtiaz-blue/10 border-imtiaz-blue/20" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <SummaryCard label="Partiels (Acomptes)" value={reconcileData.summary?.partial_count} color="text-orange-400" bg="bg-orange-400/10 border-orange-400/20" />
            <SummaryCard label="Factures orphelines" value={reconcileData.summary?.unmatched_invoices_count} color="text-imtiaz-pink" bg="bg-imtiaz-pink/10 border-imtiaz-pink/20" />
            <SummaryCard label="Mouvements orphelins" value={reconcileData.summary?.unmatched_bank_count} color="text-imtiaz-pink" bg="bg-imtiaz-pink/10 border-imtiaz-pink/20" />
          </div>

          {/* Export buttons */}
          <ExportButtons data={reconcileData} />

          {reconcileData.summary?.requires_human_review && (
            <div className="bg-amber-400/10 border border-amber-400/30 text-amber-400 rounded-xl py-3 px-5 text-sm font-semibold flex items-center gap-2">
              <AlertTriangle size={16} />
              Revue manuelle requise : certaines lignes n'ont pas pu etre rapprochees automatiquement.
            </div>
          )}

          {/* Matched pairs (EXACT, NEAR, GROUPED) */}
          {reconcileData.matched?.length > 0 && (
            <div>
              <h4 className="font-bold text-imtiaz-green text-sm mb-3 uppercase tracking-widest">
                Rapprochements ({reconcileData.matched.length})
              </h4>
              <div className="space-y-3">
                {reconcileData.matched.map((pair, i) => (
                  <MatchedRow key={i} pair={pair} index={i} />
                ))}
              </div>
            </div>
          )}

          {/* Partial matches (Acomptes) */}
          {reconcileData.partial?.length > 0 && (
            <div>
              <h4 className="font-bold text-orange-400 text-sm mb-3 uppercase tracking-widest flex items-center gap-2">
                Acomptes / Partiels ({reconcileData.partial.length})
              </h4>
              <div className="space-y-3">
                {reconcileData.partial.map((pair, i) => (
                  <MatchedRow key={`partial-${i}`} pair={pair} index={i} />
                ))}
              </div>
            </div>
          )}

          {/* Unmatched invoices */}
          <UnmatchedSection
            title="Factures non rapprochees"
            icon={<XCircle size={16} />}
            items={reconcileData.unmatched_invoices}
            color="text-imtiaz-pink"
            fields={['Fournisseur', 'Date']}
          />

          {/* Unmatched bank lines */}
          <UnmatchedSection
            title="Mouvements bancaires non identifies"
            icon={<AlertTriangle size={16} />}
            items={reconcileData.unmatched_bank}
            color="text-amber-400"
            fields={['Libelle', 'Date']}
          />
        </div>
      )}
    </div>
  );
}

function ExportButtons({ data }) {
  if (!data?.matched?.length && !data?.partial?.length) return null;

  const handleExport = (type, format) => {
    let headers, rows, filename, rootTag, rowTag;

    if (type === 'achats') {
      ({ headers, rows } = buildAchatsRows(data));
      filename = 'journal_achats';
      rootTag = 'JournalAchats';
      rowTag = 'Ecriture';
    } else if (type === 'banque') {
      ({ headers, rows } = buildBanqueRows(data));
      filename = 'journal_banque';
      rootTag = 'JournalBanque';
      rowTag = 'Ecriture';
    } else {
      ({ headers, rows } = buildRapprochementRows(data));
      filename = 'rapprochement';
      rootTag = 'Rapprochement';
      rowTag = 'Ligne';
    }

    if (format === 'csv') {
      downloadFile(toCsv(headers, rows), `${filename}.csv`, 'text/csv;charset=utf-8');
    } else {
      downloadFile(toXml(rootTag, rowTag, headers, rows), `${filename}.xml`, 'application/xml;charset=utf-8');
    }
  };

  const btnBase = "flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold uppercase tracking-wide transition-all duration-300 hover:-translate-y-0.5 border";

  return (
    <div className="space-y-3">
      <h4 className="text-white/60 text-[0.65rem] uppercase tracking-widest font-bold">Exports</h4>
      <div className="grid grid-cols-3 gap-3">
        {/* Export Achats */}
        <div className="bg-imtiaz-card/80 border border-imtiaz-blue/15 rounded-xl p-4 space-y-2">
          <p className="text-imtiaz-blue text-xs font-bold uppercase tracking-wider text-center">Journal Achats (HA)</p>
          <div className="flex gap-2">
            <button onClick={() => handleExport('achats', 'csv')} className={`${btnBase} bg-imtiaz-blue/10 border-imtiaz-blue/25 text-imtiaz-blue hover:bg-imtiaz-blue/20`}>
              <Download size={14} /> CSV
            </button>
            <button onClick={() => handleExport('achats', 'xml')} className={`${btnBase} bg-imtiaz-blue/10 border-imtiaz-blue/25 text-imtiaz-blue hover:bg-imtiaz-blue/20`}>
              <Download size={14} /> XML
            </button>
          </div>
        </div>

        {/* Export Banque */}
        <div className="bg-imtiaz-card/80 border border-cyan-400/15 rounded-xl p-4 space-y-2">
          <p className="text-cyan-400 text-xs font-bold uppercase tracking-wider text-center">Journal Banque (BQ)</p>
          <div className="flex gap-2">
            <button onClick={() => handleExport('banque', 'csv')} className={`${btnBase} bg-cyan-400/10 border-cyan-400/25 text-cyan-400 hover:bg-cyan-400/20`}>
              <Download size={14} /> CSV
            </button>
            <button onClick={() => handleExport('banque', 'xml')} className={`${btnBase} bg-cyan-400/10 border-cyan-400/25 text-cyan-400 hover:bg-cyan-400/20`}>
              <Download size={14} /> XML
            </button>
          </div>
        </div>

        {/* Export Rapprochement */}
        <div className="bg-imtiaz-card/80 border border-imtiaz-green/15 rounded-xl p-4 space-y-2">
          <p className="text-imtiaz-green text-xs font-bold uppercase tracking-wider text-center">Rapprochement</p>
          <div className="flex gap-2">
            <button onClick={() => handleExport('rapprochement', 'csv')} className={`${btnBase} bg-imtiaz-green/10 border-imtiaz-green/25 text-imtiaz-green hover:bg-imtiaz-green/20`}>
              <Download size={14} /> CSV
            </button>
            <button onClick={() => handleExport('rapprochement', 'xml')} className={`${btnBase} bg-imtiaz-green/10 border-imtiaz-green/25 text-imtiaz-green hover:bg-imtiaz-green/20`}>
              <Download size={14} /> XML
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, color, bg, icon }) {
  return (
    <div className={`${bg} border rounded-xl p-4 text-center`}>
      <p className="text-imtiaz-textMuted text-[0.65rem] uppercase tracking-widest mb-1 flex items-center justify-center gap-1">
        {icon} {label}
      </p>
      <p className={`${color} font-bold text-2xl`}>{value ?? 0}</p>
    </div>
  );
}
