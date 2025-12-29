import React, { forwardRef } from 'react'
import './Input.css'

const Input = forwardRef(({ 
  type = 'text',
  variant = 'default',
  size = 'medium',
  error = false,
  disabled = false,
  className = '',
  ...props 
}, ref) => {
  const baseClasses = 'input'
  const variantClass = `input-${variant}`
  const sizeClass = `input-${size}`
  const errorClass = error ? 'input-error' : ''
  const disabledClass = disabled ? 'input-disabled' : ''
  
  const classes = [baseClasses, variantClass, sizeClass, errorClass, disabledClass, className]
    .filter(Boolean)
    .join(' ')

  return (
    <input
      ref={ref}
      type={type}
      className={classes}
      disabled={disabled}
      {...props}
    />
  )
})

Input.displayName = 'Input'

export default Input