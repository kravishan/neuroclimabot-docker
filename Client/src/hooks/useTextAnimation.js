import { useState, useEffect } from 'react'
import { UI_CONSTANTS } from '@/constants/ui'

export const useTextAnimation = (text, isLoading, animationSpeed = UI_CONSTANTS.ANIMATION_SPEEDS.NORMAL) => {
  const [animatedText, setAnimatedText] = useState('')
  const [textComplete, setTextComplete] = useState(false)
  const [fadeIn, setFadeIn] = useState(false)

  useEffect(() => {
    if (!isLoading && text) {
      setFadeIn(true)
      
      let index = 0
      const calculatedSpeed = Math.max(10, Math.min(20, 800 / (text.length / 100)))
      const speed = animationSpeed || calculatedSpeed
      
      const animateText = () => {
        if (index <= text.length) {
          setAnimatedText(text.substring(0, index))
          index++
          setTimeout(animateText, speed)
        } else {
          setTextComplete(true)
        }
      }

      animateText()
    } else {
      setTextComplete(false)
      setAnimatedText('')
      setFadeIn(false)
    }
  }, [isLoading, text, animationSpeed])

  return { animatedText, textComplete, fadeIn, setFadeIn }
}