import React, { useState } from 'react'
import Header from './components/Header'
import Uploader from './components/Uploader'
import DataResults from './components/DataResults'
import PdfGallery from './components/PdfGallery'
import Reconciliation from './components/Reconciliation'

function App() {
  const [files, setFiles] = useState([])
  const [isScanning, setIsScanning] = useState(false)
  const [results, setResults] = useState([])
  const [error, setError] = useState(null)
  
  const [outputPdfStr, setOutputPdfStr] = useState(null)
  const [debugPdfStr, setDebugPdfStr] = useState(null)

  const handleScan = async () => {
    setIsScanning(true)
    setError(null)
    setResults([])
    setOutputPdfStr(null)
    setDebugPdfStr(null)

    const formData = new FormData()
    files.forEach((file) => {
      formData.append('data', file)
    })

    try {
      // Use the proxy configured in vite.config.js
      const res = await fetch('/api/webhook', {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        throw new Error(`Erreur serveur: ${res.status} ${res.statusText}`)
      }

      const data = await res.json()
      // Streamlit accepted a single dict or array. Wrap if needed.
      const dataArray = Array.isArray(data) ? data : [data]
      
      if (dataArray[0]?.success === false) {
        throw new Error(dataArray[0].error || "Erreur inconnue")
      }

      setResults(dataArray)
      if (dataArray[0]?.output_pdf) setOutputPdfStr(dataArray[0].output_pdf)
      if (dataArray[0]?.debug_pdf) setDebugPdfStr(dataArray[0].debug_pdf)

    } catch (err) {
      setError(err.message)
    } finally {
      setIsScanning(false)
    }
  }

  return (
    <div className="min-h-screen pb-12">
      <Header />
      
      <main className="px-6">
        <Uploader 
          files={files} 
          setFiles={setFiles} 
          isScanning={isScanning} 
          onScan={handleScan} 
        />

        {error && (
          <div className="w-full max-w-4xl mx-auto my-6 bg-imtiaz-pink/10 border border-imtiaz-pink/40 text-imtiaz-pink rounded-xl py-3.5 px-6 text-center font-semibold text-sm">
            ❌ {error}
          </div>
        )}

        {outputPdfStr && (
          <PdfGallery 
            base64Pdf={outputPdfStr} 
            debugPdf={debugPdfStr}
            results={results}
            setPdfBytes={setOutputPdfStr}
          />
        )}

        <DataResults results={results} />
        <Reconciliation results={results} />
      </main>

      {results.length > 0 && (
        <footer className="text-center text-slate-400 text-xs mt-12 mb-8 tracking-wide">
          🌊 <strong>ONWAVE</strong> &nbsp;|&nbsp; SaaS Fiduciaire Marocain &nbsp;|&nbsp; 
          Factures &bull; Relevés Bancaires &bull; Rapprochement &bull; PCGM<br />
          Propulsé par ONWAVE &bull; React &bull; n8n
        </footer>
      )}
    </div>
  )
}

export default App
