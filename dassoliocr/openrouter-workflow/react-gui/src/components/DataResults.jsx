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

const sectionIcons = {
  carte_grise: "🚗",
  cin: "🪪",
  permis_conduire: "🚦"
};

const sectionColors = {
  carte_grise: "text-imtiaz-blue",
  cin: "text-imtiaz-green",
  permis_conduire: "text-imtiaz-pink"
};

const labelsMap = {
  immatriculation: "Immatriculation",
  numero_chassis: "N° Châssis",
  date_1ere_mise_en_circulation: "Date 1ère MRC",
  marque: "Marque",
  modele: "Modèle",
  puissance_fiscale: "Puissance Fiscale",
  type_carburant: "Carburant",
  proprietaire: "Propriétaire",
  nombre_places: "Nb. Places",
  ptac: "PTAC",
  numero_cin: "N° CIN",
  nom: "Nom",
  prenom: "Prénom",
  date_naissance: "Date de Naissance",
  adresse: "Adresse",
  date_expiration: "Date d'Expiration",
  numero_permis: "N° Permis",
  categories: "Catégories",
  date_fin_validite: "Date Fin Validité",
  nom_complet: "Nom Complet"
};

export default function DataResults({ results }) {
  if (!results || results.length === 0) return null;

  return (
    <div className="w-full max-w-4xl mx-auto my-8 space-y-6">
      <div className="bg-imtiaz-green/10 border border-imtiaz-green/40 text-imtiaz-green rounded-xl py-3.5 px-6 text-center font-semibold text-sm">
        ✅ Extraction terminée avec succès !
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-imtiaz-card/80 border border-imtiaz-blue/15 rounded-xl p-4">
          <p className="text-imtiaz-textMuted text-xs mb-1">📁 Fichiers analysés</p>
          <p className="text-white font-bold text-xl">{results[0]?.filenames?.length || 0}</p>
        </div>
        <div className="bg-imtiaz-card/80 border border-imtiaz-blue/15 rounded-xl p-4">
          <p className="text-imtiaz-textMuted text-xs mb-1">📑 Documents trouvés</p>
          <p className="text-white font-bold text-xl">{results.length}</p>
        </div>
      </div>

      {results.map((resItem, docIdx) => {
        let extracted = resItem.extracted_data || resItem;
        if (Array.isArray(extracted) && extracted.length > 0) extracted = extracted[0];
        else if (Array.isArray(extracted)) extracted = {};

        const hasData = Object.values(extracted).some(v => 
          typeof v === 'object' && v !== null && Object.values(v).some(val => val && val !== 'NULL' && val !== 'null' && val !== '-')
        );

        if (!hasData) return null;

        return (
          <div key={docIdx} className="bg-imtiaz-card border-t-[3px] border-transparent shadow-lg rounded-2xl p-6 mt-4">
            <h3 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
              📋 Document {docIdx + 1}
            </h3>

            {Object.entries(extracted).map(([section, fields], i) => {
              if (['orientation', 'orientation_per_image', 'orientations', 'metadata'].includes(section.toLowerCase())) return null;
              
              if (typeof fields !== 'object' || fields === null || !Object.values(fields).some(v => v && v !== 'NULL' && v !== 'null' && v !== '-')) {
                return null;
              }

              const icon = sectionIcons[section] || "📄";
              const colorClass = sectionColors[section] || "text-imtiaz-blue";
              const title = section.replace(/_/g, " ").toUpperCase();

              return (
                <div key={section} className="mb-6 last:mb-0">
                  <h4 className={`font-bold ${colorClass} text-[0.95rem] mb-3 tracking-widest uppercase flex items-center gap-2`}>
                    {icon} {title}
                  </h4>
                  <div className="space-y-0.5">
                    {Object.entries(fields).map(([key, value]) => {
                      const label = labelsMap[key] || key.replace(/_/g, " ").toUpperCase();
                      const isNull = !value || value === 'NULL' || value === 'null' || value === '-';
                      
                      return (
                        <div key={key} className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
                          <span className="text-imtiaz-textMutedDark text-[0.78rem] font-semibold uppercase tracking-wider flex-1">
                            {label}
                          </span>
                          <span className="flex-1 right-0 flex items-center justify-end">
                            {!isNull ? (
                               <div className="flex items-center">
                                 <code className="bg-white/5 text-[#e8f0ff] px-2 py-1 rounded font-mono text-sm inline-block">
                                   {value}
                                 </code>
                                 <CopyButton text={value} />
                               </div>
                            ) : (
                               <span className="text-imtiaz-pink font-semibold text-sm">NULL</span>
                            )}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}

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
            
            {resItem.raw && (
              <div className="mt-2 text-right">
                <details className="group inline-block text-left">
                  <summary className="flex justify-end items-center gap-2 cursor-pointer text-imtiaz-pink/70 hover:text-imtiaz-pink text-xs uppercase tracking-wider font-semibold transition-colors select-none">
                    🔧 Réponse N8N Brute (JSON) <ChevronDown size={14} className="group-open:rotate-180 transition-transform" />
                  </summary>
                  <div className="mt-3 bg-black/40 border border-imtiaz-pink/20 p-4 rounded-xl relative overflow-x-auto w-full">
                     <div className="absolute top-3 right-3">
                       <CopyButton text={JSON.stringify(resItem.raw, null, 2)} />
                     </div>
                     <pre className="text-imtiaz-pink/80 font-mono text-xs whitespace-pre-wrap">{JSON.stringify(resItem.raw, null, 2)}</pre>
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
