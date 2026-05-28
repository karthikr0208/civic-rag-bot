import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { submitQuery, QueryResponse } from '../api/query'
import AnswerCard from './AnswerCard'
import SuggestionChips from './SuggestionChips'

const INITIAL_SUGGESTIONS = [
  'How does Honda Sensing work and what features does it include?',
  'What do the Maintenance Minder codes mean?',
  'How do I connect my phone via Bluetooth?',
]

function LoadingDots() {
  return (
    <div
      style={{
        display: 'flex',
        gap: 7,
        justifyContent: 'center',
        alignItems: 'center',
        padding: '36px 0',
      }}
    >
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          animate={{ scale: [1, 1.5, 1], opacity: [0.3, 1, 0.3] }}
          transition={{ repeat: Infinity, duration: 1, delay: i * 0.18 }}
          style={{
            width: 6,
            height: 6,
            background: '#CC0000',
          }}
        />
      ))}
    </div>
  )
}

export default function ChatSection() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<QueryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [suggestions, setSuggestions] = useState(INITIAL_SUGGESTIONS)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  async function handleSubmit(q?: string) {
    const text = (q ?? question).trim()
    if (!text || loading) return
    setLoading(true)
    setError(null)
    setAnswer(null)
    try {
      const result = await submitQuery(text)
      setAnswer(result)
      if (result.suggested_questions?.length) {
        setSuggestions(result.suggested_questions.slice(0, 3))
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes('429') || msg.toLowerCase().includes('quota')) {
        setError('The AI service has hit its daily limit. Please try again tomorrow.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  function handleChipClick(text: string) {
    setQuestion(text)
    handleSubmit(text)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const canSubmit = question.trim().length > 0 && !loading

  return (
    <motion.section
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.08 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      style={{
        minHeight: '100vh',
        background: '#F7F7F5',
        padding: '72px 16px 96px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      <div style={{ width: '100%', maxWidth: 720 }}>
        {/* Section eyebrow + title */}
        <div style={{ marginBottom: 48 }}>
          <p
            style={{
              fontFamily: "'Sora', system-ui, sans-serif",
              fontSize: '0.62rem',
              fontWeight: 500,
              letterSpacing: '0.24em',
              textTransform: 'uppercase',
              color: '#636363',
              marginBottom: '1rem',
            }}
          >
            Ask Your Mechanic
          </p>
          <h2
            style={{
              fontFamily: "'Cormorant Garamond', Georgia, serif",
              fontSize: 'clamp(2.4rem, 4vw, 4rem)',
              fontWeight: 300,
              color: '#1A1A1A',
              lineHeight: 0.95,
              letterSpacing: '-0.01em',
              marginBottom: '1.25rem',
            }}
          >
            What would you like<br />
            <em style={{ fontStyle: 'italic', color: '#CC0000' }}>to know?</em>
          </h2>
          <div
            style={{
              height: 2,
              width: '2.5rem',
              background: '#CC0000',
            }}
          />
        </div>

        {/* Suggestion chips — shown above input only before any answer */}
        {!answer && <SuggestionChips suggestions={suggestions} onSelect={handleChipClick} />}

        {/* Input row */}
        <div
          style={{
            background: '#ffffff',
            border: '1px solid rgba(26, 26, 26, 0.18)',
            borderRadius: 0,
            padding: '12px 12px 12px 18px',
            display: 'flex',
            alignItems: 'flex-end',
            gap: 8,
            marginBottom: 28,
          }}
        >
          <textarea
            ref={textareaRef}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your Honda Civic..."
            rows={1}
            style={{
              flex: 1,
              border: 'none',
              outline: 'none',
              resize: 'none',
              fontFamily: "'Sora', system-ui, sans-serif",
              fontSize: '0.82rem',
              fontWeight: 300,
              color: '#1A1A1A',
              background: 'transparent',
              minHeight: 26,
              maxHeight: 160,
              overflowY: 'auto',
              lineHeight: 1.7,
            }}
          />
          <button
            onClick={() => handleSubmit()}
            disabled={!canSubmit}
            style={{
              background: canSubmit ? '#CC0000' : 'rgba(26,26,26,0.12)',
              color: '#ffffff',
              border: 'none',
              borderRadius: 0,
              padding: '9px 20px',
              fontFamily: "'Sora', system-ui, sans-serif",
              fontSize: '0.65rem',
              fontWeight: 600,
              letterSpacing: '0.2em',
              textTransform: 'uppercase',
              cursor: canSubmit ? 'pointer' : 'not-allowed',
              transition: 'background 0.2s',
              flexShrink: 0,
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => {
              if (canSubmit) e.currentTarget.style.background = '#AA0000'
            }}
            onMouseLeave={(e) => {
              if (canSubmit) e.currentTarget.style.background = '#CC0000'
            }}
          >
            {loading ? '...' : 'Ask →'}
          </button>
        </div>

        {/* Answer / loading / error */}
        <AnimatePresence mode="wait">
          {loading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <LoadingDots />
            </motion.div>
          )}
          {error && !loading && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              style={{
                background: 'rgba(204, 0, 0, 0.05)',
                border: '1px solid rgba(204, 0, 0, 0.2)',
                padding: '16px 20px',
                color: '#CC0000',
                fontFamily: "'Sora', system-ui, sans-serif",
                fontSize: '0.78rem',
                fontWeight: 300,
                letterSpacing: '0.02em',
              }}
            >
              {error}
            </motion.div>
          )}
          {answer && !loading && (
            <motion.div key="answer">
              <AnswerCard result={answer} />
              <div style={{ marginTop: 20 }}>
                <SuggestionChips suggestions={suggestions} onSelect={handleChipClick} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.section>
  )
}
