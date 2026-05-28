import { motion } from 'framer-motion'
import { QueryResponse } from '../api/query'
import CitationChips from './CitationChips'

interface Props {
  result: QueryResponse
}

export default function AnswerCard({ result }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      style={{
        background: '#ffffff',
        border: '1px solid rgba(26, 26, 26, 0.18)',
        borderRadius: 0,
        padding: '28px 32px',
      }}
    >
      <div>
        {result.answer_sections.map((section, i) => (
          <p
            key={i}
            style={{
              fontFamily: "'Sora', system-ui, sans-serif",
              fontSize: '0.82rem',
              fontWeight: 300,
              lineHeight: 1.9,
              color: '#1A1A1A',
              letterSpacing: '0.01em',
              marginBottom: i < result.answer_sections.length - 1 ? 14 : 0,
            }}
          >
            {section.tooltip_text ? (
              <span className="tt-span" data-tip={section.tooltip_text}>
                {section.text}
              </span>
            ) : (
              section.text
            )}
          </p>
        ))}
      </div>

      <CitationChips citations={result.citations} />
    </motion.div>
  )
}
