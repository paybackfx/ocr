import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { FileUp, Loader2, File } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cx(...args) {
  return twMerge(clsx(...args));
}

export default function Uploader({ files, setFiles, isScanning, onScan }) {
  const onDrop = useCallback(acceptedFiles => {
    // limit to 6 files total
    const newFiles = [...files, ...acceptedFiles].slice(0, 6);
    setFiles(newFiles);
  }, [files, setFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'application/pdf': ['.pdf']
    },
    maxFiles: 6
  });

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  return (
    <div className="w-full max-w-4xl mx-auto my-6">
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-white text-lg font-semibold flex items-center gap-2">
          📎 Importation des Documents
        </h2>
      </div>
      <p className="text-[#5a7498] text-sm mb-4">
        Glissez vos documents d'assurance (CIN recto/verso, Carte Grise recto/verso, Permis). Maximum 6 fichiers.
      </p>

      <div
        {...getRootProps()}
        className={cx(
          "border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300",
          isDragActive 
            ? "border-imtiaz-blue bg-[#0d1f45]/90" 
            : "border-imtiaz-blue/40 bg-[#0d1f45]/60 hover:border-imtiaz-blue hover:bg-[#0d1f45]/90"
        )}
      >
        <input {...getInputProps()} />
        <FileUp className="w-10 h-10 text-imtiaz-blue/60 mx-auto mb-3" />
        <p className="text-imtiaz-textMuted text-lg font-medium">
          {isDragActive
            ? "Déposez les fichiers ici ..."
            : "📂 Déposez vos fichiers ici — JPG, PNG, PDF"}
        </p>
      </div>

      {files.length > 0 && (
        <div className="mt-6">
          <div className="flex flex-wrap gap-2 mb-6">
            {files.map((file, i) => (
              <div key={i} className="flex items-center gap-2 bg-imtiaz-blue/10 border border-imtiaz-blue/30 text-imtiaz-blue rounded-lg px-3 py-1 text-sm font-medium">
                <File size={14} />
                <span className="max-w-[150px] truncate">{file.name}</span>
                <span className="opacity-60 text-xs">({Math.round(file.size / 1024)} KB)</span>
                <button onClick={() => removeFile(i)} className="ml-2 hover:text-white">&times;</button>
              </div>
            ))}
          </div>

          <button
            onClick={onScan}
            disabled={isScanning}
            className="w-full bg-gradient-to-br from-imtiaz-pink to-[#c0186c] hover:from-[#ff2fa0] hover:to-imtiaz-pink text-white border-0 rounded-xl py-3 px-8 font-bold text-base tracking-wide uppercase shadow-[0_4px_20px_rgba(233,30,140,0.4)] hover:shadow-[0_6px_30px_rgba(233,30,140,0.6)] hover:-translate-y-0.5 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isScanning ? (
              <>
                <Loader2 className="animate-spin w-5 h-5" />
                🔄 Extraction en cours — Analyse IA...
              </>
            ) : (
              `🔍 Analyser ${files.length} document${files.length > 1 ? 's' : ''}`
            )}
          </button>
        </div>
      )}
    </div>
  );
}
