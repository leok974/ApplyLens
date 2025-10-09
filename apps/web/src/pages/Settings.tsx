import { useState } from 'react'
import { getRecencyScale, setRecencyScale, RecencyScale } from '../state/searchPrefs'

export default function Settings() {
  const [scale, setScale] = useState<RecencyScale>(getRecencyScale())

  function onChangeScale(e: React.ChangeEvent<HTMLSelectElement>) {
    const v = e.target.value as RecencyScale
    setScale(v)
    setRecencyScale(v)
  }

  return (
    <div style={{ padding: 20 }}>
      <h1 style={{ fontSize: 24, fontWeight: 'bold', marginBottom: 20 }}>Settings</h1>
      
      <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: 16, marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 12 }}>Search Scoring</h2>
        
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 8, fontSize: 14 }}>
            <strong>Recency Scale:</strong>
            <select
              value={scale}
              onChange={onChangeScale}
              style={{ 
                display: 'block',
                marginTop: 4,
                padding: '8px 12px',
                borderRadius: 6,
                border: '1px solid #ccc',
                fontSize: 14,
                width: '100%',
                maxWidth: 300
              }}
            >
              <option value="3d">3 days (more freshness)</option>
              <option value="7d">7 days (balanced) - Default</option>
              <option value="14d">14 days (more recall)</option>
            </select>
          </label>
          <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
            Controls the Gaussian decay scale for search result recency.
            Applies to <code>/search</code> via <code>?scale=3d|7d|14d</code> parameter.
          </div>
        </div>

        <div style={{ 
          padding: 12, 
          background: '#f0f9ff', 
          border: '1px solid #bae6fd',
          borderRadius: 6,
          fontSize: 13 
        }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Current Scoring Weights:</div>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            <li>Offer: <strong>4.0×</strong> (highest priority)</li>
            <li>Interview: <strong>3.0×</strong></li>
            <li>Others: <strong>1.0×</strong></li>
            <li>Rejection: <strong>0.5×</strong> (de-emphasized)</li>
          </ul>
        </div>
      </div>

      <div style={{ fontSize: 12, color: '#999', marginTop: 24 }}>
        More settings coming soon...
      </div>
    </div>
  )
}
