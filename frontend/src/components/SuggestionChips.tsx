import { motion } from 'framer-motion'

interface Props {
  suggestions: string[]
  onSelect: (text: string) => void
}

export default function SuggestionChips({ suggestions, onSelect }: Props) {
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px 10px',
        marginBottom: 20,
      }}
    >
      {suggestions.map((sug, i) => (
        <motion.button
          key={sug}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.07, duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          onClick={() => onSelect(sug)}
          style={{
            background: 'transparent',
            border: '1px solid rgba(26, 26, 26, 0.18)',
            borderRadius: 0,
            padding: '7px 16px',
            fontFamily: "'Sora', system-ui, sans-serif",
            fontSize: '0.65rem',
            fontWeight: 500,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: '#1A1A1A',
            cursor: 'pointer',
            lineHeight: 1.4,
            transition: 'border-color 0.15s, color 0.15s',
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
          {sug}
        </motion.button>
      ))}
    </div>
  )
}
