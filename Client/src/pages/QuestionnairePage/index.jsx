/**
 * CHI 2027 Research Questionnaire Page
 * Exports the scientifically validated research questionnaire
 */
import ResearchQuestionnaire from './ResearchQuestionnaire'

const QuestionnairePage = () => {
  return <ResearchQuestionnaire />
}

export default QuestionnairePage

/* OLD IMPLEMENTATION BELOW - KEPT FOR REFERENCE
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, AlertCircle, FileText } from 'lucide-react'
import { API_CONFIG } from '@/constants/config'
import './QuestionnairePage.css'

const OldQuestionnairePage = () => {
  const navigate = useNavigate()
  const [currentSection, setCurrentSection] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitSuccess, setSubmitSuccess] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  // Form state
  const [formData, setFormData] = useState({
    // Participant Information
    first_name: '',
    last_name: '',
    email: '',
    submission_date: new Date().toLocaleDateString('en-US'),

    // Informed Consent
    consent_study_info: false,
    consent_age_18: false,
    consent_voluntary: false,
    consent_data_collection: false,
    consent_privacy_notice: false,
    consent_data_processing: false,
    consent_publications: false,
    consent_anonymity: false,
    consent_open_science: false,

    // User Experience
    overall_experience_rating: null,
    information_accuracy: '',
    understanding_improvement: '',
    response_clarity: '',
    response_time_satisfaction: '',

    // Content & Usability
    topics_discussed: [],
    used_voice_feature: false,
    voice_experience_rating: null,
    most_useful_features: '',
    suggested_improvements: '',

    // Demographics
    age_range: '',
    education_level: '',
    field_of_study: '',
    prior_climate_knowledge: ''
  })

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleCheckboxChange = (field) => {
    setFormData(prev => ({ ...prev, [field]: !prev[field] }))
  }

  const handleTopicToggle = (topic) => {
    setFormData(prev => ({
      ...prev,
      topics_discussed: prev.topics_discussed.includes(topic)
        ? prev.topics_discussed.filter(t => t !== topic)
        : [...prev.topics_discussed, topic]
    }))
  }

  const allConsentsGiven = () => {
    return formData.consent_study_info &&
      formData.consent_age_18 &&
      formData.consent_voluntary &&
      formData.consent_data_collection &&
      formData.consent_privacy_notice &&
      formData.consent_data_processing &&
      formData.consent_publications &&
      formData.consent_anonymity &&
      formData.consent_open_science
  }

  const canProceedToNextSection = () => {
    if (currentSection === 1) {
      return allConsentsGiven()
    }
    return true
  }

  const canSubmit = () => {
    return formData.first_name && formData.last_name && formData.email && allConsentsGiven()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!canSubmit()) {
      setSubmitError('Please complete all required fields')
      return
    }

    setIsSubmitting(true)
    setSubmitError(null)

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.QUESTIONNAIRE_SUBMIT}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      })

      const data = await response.json()

      if (response.ok) {
        setSubmitSuccess(true)
        setTimeout(() => {
          navigate('/')
        }, 3000)
      } else {
        setSubmitError(data.detail || 'Failed to submit questionnaire')
      }
    } catch (error) {
      console.error('Error submitting questionnaire:', error)
      setSubmitError('An error occurred while submitting the questionnaire')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (submitSuccess) {
    return (
      <div className="questionnaire-page">
        <div className="success-message">
          <CheckCircle size={64} className="success-icon" />
          <h2>Thank You!</h2>
          <p>Your questionnaire has been submitted successfully.</p>
          <p>Redirecting to home page...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="questionnaire-page">
      <div className="questionnaire-container">
        <div className="questionnaire-header">
          <FileText size={32} />
          <h1>NeuroClima Bot Research Questionnaire</h1>
          <p className="subtitle">Help us improve climate communication through AI</p>
        </div>

        {/* Progress Indicator */}
        <div className="progress-indicator">
          <div className={`progress-step ${currentSection >= 1 ? 'active' : ''}`}>
            <div className="step-number">1</div>
            <div className="step-label">Consent</div>
          </div>
          <div className={`progress-step ${currentSection >= 2 ? 'active' : ''}`}>
            <div className="step-number">2</div>
            <div className="step-label">Experience</div>
          </div>
          <div className={`progress-step ${currentSection >= 3 ? 'active' : ''}`}>
            <div className="step-number">3</div>
            <div className="step-label">Feedback</div>
          </div>
          <div className={`progress-step ${currentSection >= 4 ? 'active' : ''}`}>
            <div className="step-number">4</div>
            <div className="step-label">About You</div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="questionnaire-form">
          {/* Section 1: Informed Consent */}
          {currentSection === 1 && (
            <div className="form-section">
              <h2>Section 1: Informed Consent</h2>
              <p className="section-description">
                Please read and confirm your understanding of the following statements. All consent items are required to participate.
              </p>

              <div className="consent-group">
                {[
                  { key: 'consent_study_info', label: 'I have read and understood the study information dated [07/2023], or it has been read to me. I have been able to ask questions about the study and my questions have been answered to my satisfaction.' },
                  { key: 'consent_age_18', label: 'I am 18 years of age or older.' },
                  { key: 'consent_voluntary', label: 'I consent voluntarily to be a participant in this study and understand that I can refuse to answer questions and I can withdraw from the study at any time, without having to give a reason.' },
                  { key: 'consent_data_collection', label: 'I give my permission for the data described in the information sheet to be collected and processed by the researchers at the University of Oulu.' },
                  { key: 'consent_privacy_notice', label: 'I have been provided with the privacy notice for scientific research participants and have had the opportunity to read it and any questions have been answered to my satisfaction.' },
                  { key: 'consent_data_processing', label: 'I give my permission for the personal data described in the Information for Subjects sheet to be processed by the researchers at the University of Oulu and its personal data processor(s) as described in the privacy notice.' },
                  { key: 'consent_publications', label: 'I consent to the use of data I provide in this study for publications, conference presentations, and reports.' },
                  { key: 'consent_anonymity', label: 'I understand that personal information collected about me that can identify me, such as my name, will not be shared beyond the study team.' },
                  { key: 'consent_open_science', label: 'I give permission for the pseudonymized experiment data (answers to questionnaires and conversations with the chatbot) that I provide to be deposited in the Open Science Foundation so it can be used for future research and learning.' }
                ].map(({ key, label }) => (
                  <label key={key} className="consent-item">
                    <input
                      type="checkbox"
                      checked={formData[key]}
                      onChange={() => handleCheckboxChange(key)}
                      required
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Section 2: User Experience */}
          {currentSection === 2 && (
            <div className="form-section">
              <h2>Section 2: User Experience</h2>
              <p className="section-description">
                Please share your experience using the NeuroClima Bot.
              </p>

              <div className="form-group">
                <label>How would you rate your overall experience with the NeuroClima Bot? *</label>
                <div className="rating-scale">
                  {[1, 2, 3, 4, 5].map(rating => (
                    <label key={rating} className="rating-option">
                      <input
                        type="radio"
                        name="overall_experience_rating"
                        value={rating}
                        checked={formData.overall_experience_rating === rating}
                        onChange={() => handleInputChange('overall_experience_rating', rating)}
                      />
                      <span className="rating-label">{rating}</span>
                    </label>
                  ))}
                </div>
                <div className="rating-labels">
                  <span>Poor</span>
                  <span>Excellent</span>
                </div>
              </div>

              {[
                { key: 'information_accuracy', label: 'The information provided by the bot was accurate and trustworthy' },
                { key: 'understanding_improvement', label: 'The bot helped me understand climate change topics better' },
                { key: 'response_clarity', label: 'The responses were clear and easy to understand' },
                { key: 'response_time_satisfaction', label: 'The bot responded in a reasonable amount of time' }
              ].map(({ key, label }) => (
                <div key={key} className="form-group">
                  <label>{label}</label>
                  <div className="agreement-scale">
                    {['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'].map(option => (
                      <label key={option} className="agreement-option">
                        <input
                          type="radio"
                          name={key}
                          value={option}
                          checked={formData[key] === option}
                          onChange={(e) => handleInputChange(key, e.target.value)}
                        />
                        <span>{option}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Section 3: Content & Usability */}
          {currentSection === 3 && (
            <div className="form-section">
              <h2>Section 3: Content & Usability</h2>
              <p className="section-description">
                Help us understand how you used the bot and what we can improve.
              </p>

              <div className="form-group">
                <label>What topics did you discuss with the bot? (Select all that apply)</label>
                <div className="checkbox-group">
                  {['Climate Science', 'Climate Policy', 'Climate Adaptation', 'Climate Mitigation', 'Health Impacts', 'Other'].map(topic => (
                    <label key={topic} className="checkbox-item">
                      <input
                        type="checkbox"
                        checked={formData.topics_discussed.includes(topic)}
                        onChange={() => handleTopicToggle(topic)}
                      />
                      <span>{topic}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label>Did you use the voice interaction feature?</label>
                <div className="radio-group">
                  <label className="radio-item">
                    <input
                      type="radio"
                      name="used_voice_feature"
                      checked={formData.used_voice_feature === true}
                      onChange={() => handleInputChange('used_voice_feature', true)}
                    />
                    <span>Yes</span>
                  </label>
                  <label className="radio-item">
                    <input
                      type="radio"
                      name="used_voice_feature"
                      checked={formData.used_voice_feature === false}
                      onChange={() => handleInputChange('used_voice_feature', false)}
                    />
                    <span>No</span>
                  </label>
                </div>
              </div>

              {formData.used_voice_feature && (
                <div className="form-group">
                  <label>How would you rate the voice interaction experience?</label>
                  <div className="rating-scale">
                    {[1, 2, 3, 4, 5].map(rating => (
                      <label key={rating} className="rating-option">
                        <input
                          type="radio"
                          name="voice_experience_rating"
                          value={rating}
                          checked={formData.voice_experience_rating === rating}
                          onChange={() => handleInputChange('voice_experience_rating', rating)}
                        />
                        <span className="rating-label">{rating}</span>
                      </label>
                    ))}
                  </div>
                  <div className="rating-labels">
                    <span>Poor</span>
                    <span>Excellent</span>
                  </div>
                </div>
              )}

              <div className="form-group">
                <label>What features did you find most useful?</label>
                <textarea
                  rows="4"
                  value={formData.most_useful_features}
                  onChange={(e) => handleInputChange('most_useful_features', e.target.value)}
                  placeholder="Tell us about the features you appreciated..."
                />
              </div>

              <div className="form-group">
                <label>What improvements would you suggest?</label>
                <textarea
                  rows="4"
                  value={formData.suggested_improvements}
                  onChange={(e) => handleInputChange('suggested_improvements', e.target.value)}
                  placeholder="Share your ideas for improvement..."
                />
              </div>
            </div>
          )}

          {/* Section 4: Demographics & Personal Information */}
          {currentSection === 4 && (
            <div className="form-section">
              <h2>Section 4: About You</h2>
              <p className="section-description">
                Please provide your information. Demographic questions are optional.
              </p>

              <div className="form-group">
                <label>First Name *</label>
                <input
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => handleInputChange('first_name', e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Last Name *</label>
                <input
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => handleInputChange('last_name', e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Email *</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  required
                />
              </div>

              <div className="divider"></div>

              <h3>Demographics (Optional)</h3>

              <div className="form-group">
                <label>Age Range</label>
                <select
                  value={formData.age_range}
                  onChange={(e) => handleInputChange('age_range', e.target.value)}
                >
                  <option value="">Select...</option>
                  <option value="18-24">18-24</option>
                  <option value="25-34">25-34</option>
                  <option value="35-44">35-44</option>
                  <option value="45-54">45-54</option>
                  <option value="55-64">55-64</option>
                  <option value="65+">65+</option>
                  <option value="prefer-not-to-say">Prefer not to say</option>
                </select>
              </div>

              <div className="form-group">
                <label>Education Level</label>
                <select
                  value={formData.education_level}
                  onChange={(e) => handleInputChange('education_level', e.target.value)}
                >
                  <option value="">Select...</option>
                  <option value="high-school">High School</option>
                  <option value="bachelors">Bachelor's Degree</option>
                  <option value="masters">Master's Degree</option>
                  <option value="phd">PhD</option>
                  <option value="other">Other</option>
                  <option value="prefer-not-to-say">Prefer not to say</option>
                </select>
              </div>

              <div className="form-group">
                <label>Field of Study or Work (Optional)</label>
                <input
                  type="text"
                  value={formData.field_of_study}
                  onChange={(e) => handleInputChange('field_of_study', e.target.value)}
                  placeholder="e.g., Environmental Science, Computer Science..."
                />
              </div>

              <div className="form-group">
                <label>Prior Knowledge of Climate Change</label>
                <select
                  value={formData.prior_climate_knowledge}
                  onChange={(e) => handleInputChange('prior_climate_knowledge', e.target.value)}
                >
                  <option value="">Select...</option>
                  <option value="none">None</option>
                  <option value="basic">Basic</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
            </div>
          )}

          {/* Error Message */}
          {submitError && (
            <div className="error-message">
              <AlertCircle size={20} />
              <span>{submitError}</span>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="form-navigation">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setCurrentSection(prev => Math.max(1, prev - 1))}
              disabled={currentSection === 1}
            >
              Previous
            </button>

            {currentSection < 4 ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setCurrentSection(prev => prev + 1)}
                disabled={!canProceedToNextSection()}
              >
                Next
              </button>
            ) : (
              <button
                type="submit"
                className="btn btn-success"
                disabled={!canSubmit() || isSubmitting}
              >
                {isSubmitting ? 'Submitting...' : 'Submit Questionnaire'}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
*/
