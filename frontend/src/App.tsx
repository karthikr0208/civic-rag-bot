import { useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import Hero from './components/Hero'
import ChatSection from './components/ChatSection'

export default function App() {
  const heroRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  })
  const heroOpacity = useTransform(scrollYProgress, [0.4, 1], [1, 0])
  const heroScale = useTransform(scrollYProgress, [0, 1], [1, 0.96])

  return (
    <div>
      <motion.div ref={heroRef} style={{ opacity: heroOpacity, scale: heroScale }}>
        <Hero />
      </motion.div>
      <ChatSection />
    </div>
  )
}
