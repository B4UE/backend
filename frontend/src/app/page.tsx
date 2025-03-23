'use client'

import { useState, useRef, useEffect } from 'react'
import HealthConditions from '@/components/HealthConditions'
import Camera from '@/components/Camera'
import AnalysisResults from '@/components/AnalysisResults'

export default function Home() {
  const [healthConditions, setHealthConditions] = useState<Set<string>>(new Set())
  const [photo, setPhoto] = useState<string>('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResults, setAnalysisResults] = useState<any>(null)

  const handleAnalyze = async () => {
    if (!photo) {
      alert('Please capture a photo first')
      return
    }

    const allergies = []
    if (document.getElementById('nutAllergy') as HTMLInputElement)?.checked) allergies.push('nuts')
    if (document.getElementById('dairyAllergy') as HTMLInputElement)?.checked) allergies.push('dairy')
    if (document.getElementById('shellfishAllergy') as HTMLInputElement)?.checked) allergies.push('shellfish')

    const data = {
      image: photo,
      dietType: (document.getElementById('dietType') as HTMLSelectElement)?.value || 'none',
      allergies,
      healthConditions: Array.from(healthConditions)
    }

    setIsAnalyzing(true)

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
      })

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.error || `HTTP error! status: ${response.status}`)
      }
      
      if (result.success) {
        setAnalysisResults(result.analysis)
      } else {
        throw new Error(result.error || 'Unknown error occurred')
      }
    } catch (error) {
      alert('Error analyzing ingredients: ' + (error as Error).message)
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <main className="container mt-5">
      <h1 className="text-center mb-4">Ingredient Health Analyzer</h1>
      
      <Camera 
        onPhotoCapture={setPhoto} 
        photo={photo}
      />

      <div className="health-preferences">
        <h3>Health Profile</h3>
        
        <div className="mb-3">
          <label htmlFor="dietType" className="form-label">Diet Type:</label>
          <select className="form-select" id="dietType">
            <option value="none">No specific diet</option>
            <option value="vegetarian">Vegetarian</option>
            <option value="vegan">Vegan</option>
            <option value="keto">Keto</option>
            <option value="paleo">Paleo</option>
            <option value="gluten-free">Gluten-free</option>
          </select>
        </div>

        <div className="mb-3">
          <label className="form-label">Allergies:</label>
          <div className="form-check">
            <input className="form-check-input" type="checkbox" id="nutAllergy" />
            <label className="form-check-label" htmlFor="nutAllergy">Nuts</label>
          </div>
          <div className="form-check">
            <input className="form-check-input" type="checkbox" id="dairyAllergy" />
            <label className="form-check-label" htmlFor="dairyAllergy">Dairy</label>
          </div>
          <div className="form-check">
            <input className="form-check-input" type="checkbox" id="shellfishAllergy" />
            <label className="form-check-label" htmlFor="shellfishAllergy">Shellfish</label>
          </div>
        </div>

        <HealthConditions
          conditions={healthConditions}
          onConditionsChange={setHealthConditions}
        />
      </div>

      {photo && (
        <div className="text-center mt-4">
          <button 
            className="btn btn-primary btn-lg" 
            onClick={handleAnalyze}
            disabled={isAnalyzing}
          >
            {isAnalyzing ? 'Analyzing...' : 'Analyze Ingredients'}
          </button>
        </div>
      )}

      {analysisResults && (
        <AnalysisResults results={analysisResults} />
      )}
    </main>
  )
}
