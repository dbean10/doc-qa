interface TokenDisplayProps {
    inputTokens: number | null
    outputTokens: number | null
  }
  
  export function TokenDisplay({ inputTokens, outputTokens }: TokenDisplayProps) {
    if (inputTokens === null || outputTokens === null) return null
  
    return (
      <div style={{
        fontSize: '0.7rem',
        color: '#999',
        textAlign: 'right',
        padding: '0.25rem 0.75rem',
        borderTop: '1px solid #f0f0f0',
      }}>
        {inputTokens.toLocaleString()} in · {outputTokens.toLocaleString()} out
      </div>
    )
  }