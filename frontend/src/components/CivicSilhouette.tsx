import { motion } from 'framer-motion'
import civicImg from '../assets/Civic assembled.webp'

export default function CivicSilhouette() {
  return (
    <motion.img
      src={civicImg}
      alt="Honda Civic"
      initial={{ x: 80, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
      style={{
        maxWidth: 680,
        width: '100%',
        mixBlendMode: 'multiply',
        userSelect: 'none',
        pointerEvents: 'none',
      }}
    />
  )
}
