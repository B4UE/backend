'use client'

interface AnalysisResultsProps {
  results: {
    identified_ingredients: string[]
    health_benefits: string[]
    health_risks: string[]
    diet_compatibility: {
      status: 'positive' | 'negative'
      details: string[]
    }
    health_impact: {
      status: 'positive' | 'negative'
      details: string[]
    }
  }
}

function ResultCard({ 
  title, 
  items, 
  cardClass = '' 
}: { 
  title: string
  items: string[]
  cardClass?: string 
}) {
  return (
    <div className={`card mb-3 ${cardClass}`}>
      <div className="card-body">
        <h5 className="card-title">{title}</h5>
        <ul className="list-group list-group-flush">
          {items.map((item, index) => (
            <li key={index} className="list-group-item">{item}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default function AnalysisResults({ results }: AnalysisResultsProps) {
  return (
    <div className="mt-4">
      {/* Ingredients Card */}
      <ResultCard 
        title="Identified Ingredients"
        items={results.identified_ingredients}
      />

      {/* Health Benefits Card */}
      <ResultCard 
        title="Health Benefits"
        items={results.health_benefits}
        cardClass="border-success"
      />

      {/* Health Risks Card */}
      <ResultCard 
        title="Health Risks"
        items={results.health_risks}
        cardClass="border-danger"
      />

      {/* Diet Compatibility Card */}
      <ResultCard 
        title="Diet & Allergy Compatibility"
        items={results.diet_compatibility.details}
        cardClass={results.diet_compatibility.status === 'positive' 
          ? 'border-success bg-success bg-opacity-10' 
          : 'border-warning bg-warning bg-opacity-10'}
      />

      {/* Health Impact Card */}
      <ResultCard 
        title="Impact on Health Conditions"
        items={results.health_impact.details}
        cardClass={results.health_impact.status === 'positive' 
          ? 'border-success bg-success bg-opacity-10' 
          : 'border-warning bg-warning bg-opacity-10'}
      />
    </div>
  )
}
