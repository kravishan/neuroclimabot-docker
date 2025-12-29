import React from 'react'
import { User } from 'lucide-react'
import './UserMessage.css'

const UserMessage = ({ content }) => {
  return (
    <div className="typed-message-container slide-in-bottom">
      <p className="typed-message" aria-label={`User message: ${content}`}>
        {content}
      </p>
      <button className="user-icon-button" aria-label="User Profile">
        <User size={24} className="user-icon" />
      </button>
    </div>
  )
}

export default UserMessage