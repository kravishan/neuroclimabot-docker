import React, { forwardRef } from 'react'
import './Button.css'

const Button = forwardRef(({ 
  children,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  className = '',
  ...props 
}, ref) => {
  const baseClasses = 'button'
  const variantClass = `button-${variant}`
  const sizeClass = `button-${size}`
  const disabledClass = disabled ? 'button-disabled' : ''
  
  const classes = [baseClasses, variantClass, sizeClass, disabledClass, className]
    .filter(Boolean)
    .join(' ')

  return (
    <button
      ref={ref}
      className={classes}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  )
})

Button.displayName = 'Button'

export default Button