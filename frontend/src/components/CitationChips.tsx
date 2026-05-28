import { motion } from 'framer-motion'
import { Citation } from '../api/query'

interface Props {
  citations: Citation[]
}

export default function CitationChips({ citations }: Props) {
  if (!citations?.length) return null

  return (
    <div
      style={{
        marginTop: 20,
        paddingTop: 16,
        borderTop: '1px solid rgba(26, 26, 26, 0.12)',
      }}
    >
      <p
        style={{
          fontFamily: "'Sora', system-ui, sans-serif",
          fontSize: '0.58rem',
          fontWeight: 500,
          textTransform: 'uppercase',
          letterSpacing: '0.2em',
          color: '#636363',
          marginBottom: 10,
        }}
      >
        References
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 8px' }}>
        {citations.map((cite, i) => (
          <motion.a
            key={i}
            href={cite.url}
            target="_blank"
            rel="noopener noreferrer"
            initial={{ opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05, duration: 0.2 }}
            style={{
              display: 'inline-block',
              padding: '5px 14px',
              background: 'transparent',
              border: '1px solid rgba(26, 26, 26, 0.18)',
              borderRadius: 0,
              fontFamily: "'Sora', system-ui, sans-serif",
              fontSize: '0.65rem',
              fontWeight: 500,
              letterSpacing: '0.08em',
              color: '#1A1A1A',
              textDecoration: 'none',
              transition: 'border-color 0.12s, color 0.12s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = '#CC0000'
              e.currentTarget.style.color = '#CC0000'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(26, 26, 26, 0.18)'
              e.currentTarget.style.color = '#1A1A1A'
            }}
          >
            {cite.label}
          </motion.a>
        ))}
      </div>
    </div>
  )
}
