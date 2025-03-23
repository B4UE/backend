'use client'

import { useState } from 'react'

interface HealthConditionsProps {
  conditions: Set<string>
  onConditionsChange: (conditions: Set<string>) => void
}

export default function HealthConditions({ conditions, onConditionsChange }: HealthConditionsProps) {
  const [inputValue, setInputValue] = useState('')

  const addCondition = (e: React.FormEvent) => {
    e.preventDefault()
    const condition = inputValue.trim()
    if (condition) {
      const newConditions = new Set(conditions)
      newConditions.add(condition)
      onConditionsChange(newConditions)
      setInputValue('')
    }
  }

  const removeCondition = (conditionToRemove: string) => {
    const newConditions = new Set(conditions)
    newConditions.delete(conditionToRemove)
    onConditionsChange(newConditions)
  }

  return (
    <div className="mb-3">
      <label className="form-label">Health Conditions:</label>
      <form onSubmit={addCondition} className="input-group mb-3">
        <input
          type="text"
          className="form-control"
          placeholder="Enter health condition"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
        />
        <button 
          className="btn btn-outline-secondary" 
          type="submit"
        >
          Add
        </button>
      </form>
      
      <div className="condition-tags">
        {Array.from(conditions).map((condition) => (
          <span key={condition} className="condition-tag">
            {condition}
            <span 
              className="remove-condition"
              onClick={() => removeCondition(condition)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  removeCondition(condition)
                }
              }}
            >
              &times;
            </span>
          </span>
        ))}
      </div>
    </div>
  )
}
