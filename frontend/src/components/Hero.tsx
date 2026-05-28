import { motion } from 'framer-motion'
import CivicSilhouette from './CivicSilhouette'

export default function Hero() {
  return (
    <section
      style={{
        minHeight: '100vh',
        background: '#F7F7F5',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Top accent bar — matches website gradient */}
      <div
        style={{
          height: 2,
          background: 'linear-gradient(90deg, transparent 0%, #CC0000 35%, #CC0000 65%, transparent 100%)',
          flexShrink: 0,
        }}
      />

      {/* Two-column layout: text left, car right */}
      <div
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          alignItems: 'center',
          width: '100%',
          maxWidth: 1280,
          margin: '0 auto',
          padding: '4rem 5vw 2rem',
          gap: '2rem',
        }}
      >
        {/* Left: text */}
        <div>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            style={{
              fontFamily: "'Sora', system-ui, sans-serif",
              fontSize: '0.62rem',
              fontWeight: 500,
              letterSpacing: '0.24em',
              textTransform: 'uppercase',
              color: '#636363',
              marginBottom: '1.75rem',
            }}
          >
            Powered by Service Manual
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            style={{
              fontFamily: "'Cormorant Garamond', Georgia, serif",
              fontSize: 'clamp(3.2rem, 5vw, 5.8rem)',
              fontWeight: 300,
              color: '#1A1A1A',
              lineHeight: 0.92,
              letterSpacing: '-0.02em',
              marginBottom: '2rem',
            }}
          >
            Your Honda<br />
            Civic's{' '}
            <em style={{ color: '#CC0000', fontStyle: 'italic' }}>
              AI<br />Mechanic
            </em>
          </motion.h1>

          {/* Red rule */}
          <motion.div
            initial={{ scaleX: 0, opacity: 0 }}
            animate={{ scaleX: 1, opacity: 1 }}
            transition={{ duration: 0.45, delay: 0.28, ease: [0.22, 1, 0.36, 1] }}
            style={{
              height: 2,
              width: '2.5rem',
              background: '#CC0000',
              marginBottom: '1.5rem',
              transformOrigin: 'left',
            }}
          />

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.35, ease: [0.22, 1, 0.36, 1] }}
            style={{
              fontFamily: "'Sora', system-ui, sans-serif",
              fontSize: '0.82rem',
              fontWeight: 300,
              lineHeight: 1.9,
              color: '#636363',
              maxWidth: '34ch',
            }}
          >
            Ask any question about your Honda Civic.<br />
            Instant answers from the official service manual — with page citations.
          </motion.p>
        </div>

        {/* Right: car */}
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <CivicSilhouette />
        </div>
      </div>

      {/* Scroll cue */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          paddingBottom: '2.5rem',
          flexShrink: 0,
        }}
      >
        <motion.div
          animate={{ opacity: [0.35, 1, 0.35] }}
          transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
          style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}
        >
          <div
            style={{
              width: 1,
              height: 36,
              background: 'linear-gradient(to bottom, #CC0000, transparent)',
            }}
          />
          <span
            style={{
              fontFamily: "'Sora', system-ui, sans-serif",
              fontSize: '0.52rem',
              letterSpacing: '0.22em',
              textTransform: 'uppercase',
              color: '#636363',
            }}
          >
            Scroll
          </span>
        </motion.div>
      </div>
    </section>
  )
}
