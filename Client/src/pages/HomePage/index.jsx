import React from 'react'
import ChatInput from '@/components/forms/ChatInput'
import './HomePage.css'

const HomePage = ({ selectedLanguage, difficultyLevel }) => {
  return (
    <div className="home-page">
      <ChatInput 
        selectedLanguage={selectedLanguage} 
        difficultyLevel={difficultyLevel} 
      />
    </div>
  )
}

export default HomePage