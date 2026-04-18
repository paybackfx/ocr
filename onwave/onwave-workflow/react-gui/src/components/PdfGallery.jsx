import React, { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { Link, RotateCw, Eye } from 'lucide-react';
import { PDFDocument, degrees } from 'pdf-lib';
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

// Initialize PDF.js worker locally to prevent unpkg freeze on tab restore
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

export default function PdfGallery({ base64Pdf, results, setPdfBytes, debugPdf }) {
  const [numPages, setNumPages] = useState(null);
  const [pageRotations, setPageRotations] = useState([]);
  const [pageSelections, setPageSelections] = useState([]);

  useEffect(() => {
    if (numPages) {
      setPageRotations(new Array(numPages).fill(0));
      setPageSelections(new Array(numPages).fill(false));
    }
  }, [numPages, base64Pdf]); // Reset when base64Pdf changes entirely

  function onDocumentLoadSuccess({ numPages }) {
    setNumPages(numPages);
  }

  const toggleSelection = (idx) => {
    const newSels = [...pageSelections];
    newSels[idx] = !newSels[idx];
    setPageSelections(newSels);
  };

  const rotatePage = (idx) => {
    const newRots = [...pageRotations];
    newRots[idx] = (newRots[idx] + 90) % 360;
    setPageRotations(newRots);
  };

  const rotateAll = (direction) => {
    setPageRotations(pageRotations.map(r => (r + direction + 360) % 360));
  };

  // Merge selected pages
  const handleMerge = async () => {
    const selectedIndices = pageSelections.map((sel, i) => sel ? i : -1).filter(i => i !== -1);
    if (selectedIndices.length < 2) return;

    try {
      // Decode current pdf
      const binaryString = atob(base64Pdf);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      const pdfDoc = await PDFDocument.load(bytes);
      const pages = pdfDoc.getPages();

      let totalHeight = 0;
      let maxWidth = 0;
      const pagesToMerge = [];

      for (const idx of selectedIndices) {
        const page = pages[idx];
        const rot = pageRotations[idx] || 0;
        const { width, height } = page.getSize();

        // If landscape (90 or 270), swap effective width/height
        const isLandscape = rot % 180 !== 0;
        const effWidth = isLandscape ? height : width;
        const effHeight = isLandscape ? width : height;

        if (effWidth > maxWidth) maxWidth = effWidth;
        totalHeight += effHeight;

        pagesToMerge.push({ idx, page, rot, effWidth, effHeight, width, height });
      }

      // Create new page at the first selected index
      const insertPos = selectedIndices[0];
      const newPage = pdfDoc.insertPage(insertPos, [maxWidth, totalHeight]);

      let currentY = totalHeight;

      for (const item of pagesToMerge) {
        const embeddedPage = await pdfDoc.embedPage(item.page);

        // Scale everything to match the maximum width
        const scale = maxWidth / item.effWidth;
        const S_W = item.width * scale;
        const S_H = item.height * scale;

        currentY -= item.effHeight * scale;

        let x = 0, y = 0, angle = 0;
        if (item.rot === 0) {
          x = 0;
          y = currentY;
          angle = 0;
        } else if (item.rot === 90) {
          x = 0;
          y = currentY + S_W;
          angle = -90;
        } else if (item.rot === 180) {
          x = S_W;
          y = currentY + S_H;
          angle = -180;
        } else if (item.rot === 270) {
          x = S_H;
          y = currentY;
          angle = 90;
        }

        newPage.drawPage(embeddedPage, {
          x,
          y,
          width: S_W,
          height: S_H,
          rotate: degrees(angle)
        });
      }

      // Remove the original pages (all indices shifted by +1 because we inserted a page BEFORE them)
      const pagesToDelete = [...selectedIndices].sort((a, b) => b - a);
      for (const p of pagesToDelete) {
        pdfDoc.removePage(p + 1);
      }

      const mergedPdfBytes = await pdfDoc.save();

      let mergedBinaryString = '';
      for (let i = 0; i < mergedPdfBytes.byteLength; i++) {
        mergedBinaryString += String.fromCharCode(mergedPdfBytes[i]);
      }

      const newBase64 = btoa(mergedBinaryString);

      // Update state and refresh
      setPdfBytes(newBase64);
      // Let the useEffect handle resetting selections once new base64Pdf is passed down
    } catch (err) {
      console.error("Erreur fusion PDF", err);
      alert("Une erreur s'est produite lors de la fusion des documents.");
    }
  };

  // Convert b64, apply rotations, download
  const handleDownload = async (b64, filename) => {
    try {
      const binaryString = atob(b64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      const pdfDoc = await PDFDocument.load(bytes);
      const pages = pdfDoc.getPages();

      for (let i = 0; i < pages.length; i++) {
        if (pageRotations[i]) {
          const currentRotation = pages[i].getRotation().angle;
          pages[i].setRotation(degrees(currentRotation + pageRotations[i]));
        }
      }

      const pdfBytes = await pdfDoc.save();
      const blob = new Blob([pdfBytes], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Error generating PDF", e);
    }
  };

  const selectedCount = pageSelections.filter(Boolean).length;

  return (
    <div className="w-full max-w-4xl mx-auto mt-8">
      <hr className="border-t border-imtiaz-blue/10 my-8" />
      <h2 className="text-white text-lg font-semibold flex items-center gap-2 mb-6">
        🔄 Aperçu et Correction de Rotation
      </h2>

      {/* Global Rotations */}
      <div className="flex justify-center gap-4 mb-2">
        <button onClick={() => rotateAll(-90)} className="bg-[#2e3b4e]/80 text-imtiaz-textMuted border border-imtiaz-blue/20 rounded-lg px-6 py-2 hover:bg-imtiaz-pink/50 hover:text-white hover:border-imtiaz-pink transition-all">
          ↺
        </button>
        <button onClick={() => rotateAll(90)} className="bg-[#2e3b4e]/80 text-imtiaz-textMuted border border-imtiaz-blue/20 rounded-lg px-6 py-2 hover:bg-imtiaz-pink/50 hover:text-white hover:border-imtiaz-pink transition-all">
          ↻
        </button>
      </div>
      <p className="text-center text-imtiaz-textMutedDark text-xs mb-6">
        ... ou utiliser les boutons sous chaque page
      </p>

      {/* Gallery */}
      <div className="flex justify-center">
        <Document
          file={`data:application/pdf;base64,${base64Pdf}`}
          onLoadSuccess={onDocumentLoadSuccess}
          className="flex flex-wrap justify-center gap-6"
        >
          {Array.from({ length: numPages || 0 }, (_, i) => {
            const rot = pageRotations[i];
            const isSel = pageSelections[i];
            return (
              <div key={i} className="flex flex-col items-center">
                <div
                  className={`bg-[#1a2234] border-2 rounded-xl w-[180px] h-[180px] p-2 flex items-center justify-center relative transition-all duration-200 overflow-hidden ${isSel ? 'border-imtiaz-pink shadow-[0_0_16px_rgba(233,30,140,0.4)]' : 'border-[#2e3b4e] hover:border-imtiaz-blue/50'}`}
                >
                  <span className="absolute top-1 right-1.5 bg-black/60 text-white text-[10px] font-bold px-1.5 py-0.5 rounded z-10">
                    {i + 1}
                  </span>
                  {isSel && (
                    <span className="absolute top-1 left-1.5 bg-imtiaz-pink text-white text-[10px] font-bold px-1.5 py-0.5 rounded z-10">
                      ✓
                    </span>
                  )}

                  <div style={{ transform: `rotate(${rot}deg)`, transition: 'transform 0.3s ease' }}>
                    <Page
                      pageNumber={i + 1}
                      width={160}
                      renderTextLayer={false}
                      renderAnnotationLayer={false}
                    />
                  </div>
                </div>

                {/* The magically perfectly centered buttons */}
                <div className="flex gap-1.5 mt-2">
                  <button
                    onClick={() => rotatePage(i)}
                    className="w-7 h-7 bg-[#2e3b4e]/80 text-imtiaz-textMuted border border-imtiaz-blue/20 rounded-md hover:bg-imtiaz-pink/50 hover:text-white hover:border-imtiaz-pink transition-all flex items-center justify-center text-sm"
                  >
                    ↻
                  </button>
                  <button
                    onClick={() => toggleSelection(i)}
                    className="w-7 h-7 bg-[#2e3b4e]/80 text-imtiaz-textMuted border border-imtiaz-blue/20 rounded-md hover:bg-imtiaz-pink/50 hover:text-white hover:border-imtiaz-pink transition-all flex items-center justify-center text-sm"
                  >
                    {isSel ? "✓" : "☐"}
                  </button>
                </div>
              </div>
            );
          })}
        </Document>
      </div>

      {selectedCount >= 2 && (
        <div className="mt-8 text-center max-w-sm mx-auto">
          <p className="text-imtiaz-pink text-sm font-semibold mb-3">
            🔗 {selectedCount} pages sélectionnées
          </p>
          <button
            onClick={handleMerge}
            className="w-full bg-gradient-to-br from-imtiaz-pink to-[#c0186c] text-white py-2.5 rounded-xl font-bold text-sm shadow-[0_4px_20px_rgba(233,30,140,0.4)]"
          >
            🔗 Fusionner les pages sélectionnées
          </button>
        </div>
      )}

      {/* Downloads */}
      <hr className="border-t border-imtiaz-blue/10 my-8" />
      <h2 className="text-white text-lg font-semibold flex items-center gap-2 mb-4">
        📥 Documents Générés
      </h2>
      <div className="grid grid-cols-2 gap-4">
        <button
          onClick={() => handleDownload(base64Pdf, "document_client.pdf")}
          className="bg-[#2e3b4e]/80 text-imtiaz-textMuted border border-imtiaz-blue/20 rounded-xl py-3 text-sm font-semibold hover:bg-imtiaz-pink/50 hover:text-white hover:border-imtiaz-pink transition-all flex items-center justify-center gap-2"
        >
          <Eye size={16} /> Télécharger PDF Client (Crop Clean)
        </button>
        {debugPdf && (
          <button
            onClick={() => handleDownload(debugPdf, "document_debug.pdf")}
            className="bg-[#2e3b4e]/80 text-imtiaz-textMuted border border-imtiaz-blue/20 rounded-xl py-3 text-sm font-semibold hover:bg-imtiaz-pink/50 hover:text-white hover:border-imtiaz-pink transition-all flex items-center justify-center gap-2"
          >
            🔍 Télécharger PDF Debug (Filtres IA)
          </button>
        )}
      </div>
    </div>
  );
}
