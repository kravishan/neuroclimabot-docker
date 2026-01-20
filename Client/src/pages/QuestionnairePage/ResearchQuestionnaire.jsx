/**
 * Research Questionnaire Component - University of Oulu
 * NeuroClima Post-Interaction Evaluation
 *
 * Validated Instruments:
 * - UEQ-S (User Experience Questionnaire - Short)
 * - Human-AI Trust Scale
 * - NASA-TLX (Task Load Index)
 * - Task Success & Information Finding Assessment
 * - Document Quality Evaluation (ResQue-adapted)
 * - Conversational Quality Assessment
 * - Behavioral Intentions Scale
 */

import React, { useState, useEffect } from 'react'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { useNavigate } from 'react-router-dom'
import {
  CheckCircle, AlertCircle, FileText, ChevronRight, ChevronLeft,
  Info, Users, Target, TrendingUp, MessageSquare, ExternalLink,
  ClipboardCheck, FileSearch, MessageCircle
} from 'lucide-react'
import { API_CONFIG } from '@/constants/config'
import {
  PRIMARY_PURPOSE_OPTIONS,
  TASK_TYPES,
  TASK_SUCCESS_ITEMS,
  INFORMATION_FINDING_ITEMS,
  DOCUMENT_QUALITY_ITEMS,
  INFORMATION_ADEQUACY_ITEMS,
  CONVERSATIONAL_QUALITY_ITEMS,
  UEQ_S_ITEMS,
  TRUST_SCALE_ITEMS,
  NASA_TLX_SUBSCALES,
  RAG_TRANSPARENCY_ITEMS,
  BEHAVIORAL_INTENTIONS_ITEMS,
  STP_EVALUATION_ITEMS,
  KG_VISUALIZATION_ITEMS,
  MULTILINGUAL_EVALUATION_ITEMS,
  DEMOGRAPHICS,
  CONSENT_INFORMATION
} from '@/constants/questionnaireData.js'
import './ResearchQuestionnaire.css'

const ResearchQuestionnaire = () => {
  const navigate = useNavigate()
  const [currentSection, setCurrentSection] = useState(0)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitSuccess, setSubmitSuccess] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [showConsentDetails, setShowConsentDetails] = useState(false)

  useDocumentTitle('Feedback Questionnaire - NeuroClima Bot')

  // Form state
  const [formData, setFormData] = useState({
    // Participant Information
    participant_id: `P${Date.now()}`,
    email: '',

    // Demographics
    age_range: '',
    education_level: '',
    country: '',
    native_language: '',
    prior_climate_knowledge: '',
    prior_ai_experience: '',

    // Single Consent Checkbox
    consent_all: false,

    // Section 1: Your Recent Experience
    primary_purpose: '',
    other_purpose: '',
    task_type: [],

    // Section 2: Task Success & Completion
    task_success: {},
    info_finding: {},

    // Section 3: Document & Source Quality
    doc_quality: {},
    info_adequacy: {},

    // Section 4: UEQ-S (8 items, 1-7 scale)
    ueq_s: {},

    // Section 5: Trust Scale (12 items, 1-7 scale)
    trust_scale: {},

    // Section 6: NASA-TLX (6 subscales, 0-20 scale)
    nasa_tlx: {},

    // Section 7: Conversational Quality (5 items, 1-7 scale)
    conversational_quality: {},

    // Section 8: Feature-Specific Evaluations
    stp_evaluation: {}, // 4 items
    kg_visualization: {}, // 5 items
    multilingual: {}, // 3 items
    used_kg_viz: null,
    used_non_english: null,

    // Section 9: RAG Transparency & Behavioral Intentions
    rag_transparency: {}, // 5 items, 1-7 scale
    behavioral_intentions: {}, // 5 items

    // Section 10: Open-Ended Feedback
    most_useful_features: '',
    suggested_improvements: '',
    additional_comments: '',

    // Metadata
    submission_date: new Date().toISOString(),
    time_started: new Date().toISOString(),
    time_per_section: {}
  })

  // Track section start times for analytics
  const [sectionStartTime, setSectionStartTime] = useState(Date.now())

  useEffect(() => {
    setSectionStartTime(Date.now())
  }, [currentSection])

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleNestedChange = (category, itemId, value) => {
    setFormData(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [itemId]: value
      }
    }))
  }

  const handleTaskTypeToggle = (taskValue) => {
    setFormData(prev => {
      const currentTypes = prev.task_type || []
      const newTypes = currentTypes.includes(taskValue)
        ? currentTypes.filter(t => t !== taskValue)
        : [...currentTypes, taskValue]
      return { ...prev, task_type: newTypes }
    })
  }

  const recordSectionTime = () => {
    const timeSpent = Date.now() - sectionStartTime
    setFormData(prev => ({
      ...prev,
      time_per_section: {
        ...prev.time_per_section,
        [`section_${currentSection}`]: timeSpent / 1000 // Convert to seconds
      }
    }))
  }

  const canProceedToNextSection = () => {
    switch (currentSection) {
      case 0: // Consent & Demographics
        return formData.consent_all &&
               formData.age_range &&
               formData.education_level &&
               formData.native_language
      case 1: // Your Recent Experience
        return formData.primary_purpose &&
               (formData.primary_purpose !== 'other' || formData.other_purpose) &&
               formData.task_type.length > 0
      case 2: // Task Success & Completion
        // task_accomplished and goal_satisfaction are required, specific_goal is optional
        const requiredTaskFields = ['task_accomplished', 'goal_satisfaction']
        const hasRequiredTaskFields = requiredTaskFields.every(field => formData.task_success[field] !== undefined)
        return hasRequiredTaskFields &&
               Object.keys(formData.info_finding).length === INFORMATION_FINDING_ITEMS.length
      case 3: // Document & Source Quality
        return Object.keys(formData.doc_quality).length === DOCUMENT_QUALITY_ITEMS.length &&
               Object.keys(formData.info_adequacy).length === INFORMATION_ADEQUACY_ITEMS.length
      case 4: // UEQ-S
        return Object.keys(formData.ueq_s).length === 8
      case 5: // Trust Scale
        return Object.keys(formData.trust_scale).length === 12
      case 6: // NASA-TLX
        return Object.keys(formData.nasa_tlx).length === 6
      case 7: // Conversational Quality
        return Object.keys(formData.conversational_quality).length === CONVERSATIONAL_QUALITY_ITEMS.length
      case 8: // Feature-Specific Evaluations
        // Check if user indicated they used features
        if (formData.used_kg_viz === null || formData.used_non_english === null) {
          return false
        }
        // If they used features, they must complete evaluations (STP is always present)
        if (Object.keys(formData.stp_evaluation).length < 4) return false
        if (formData.used_kg_viz && Object.keys(formData.kg_visualization).length < 5) return false
        if (formData.used_non_english && Object.keys(formData.multilingual).length < 3) return false
        return true
      case 9: // RAG Transparency & Behavioral Intentions
        return Object.keys(formData.rag_transparency).length === 5 &&
               Object.keys(formData.behavioral_intentions).length === 5
      case 10: // Open-Ended Feedback
        return true // Optional
      default:
        return false
    }
  }

  const handleNext = () => {
    recordSectionTime()
    setCurrentSection(prev => prev + 1)
    window.scrollTo(0, 0)
  }

  const handlePrevious = () => {
    recordSectionTime()
    setCurrentSection(prev => prev - 1)
    window.scrollTo(0, 0)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!canProceedToNextSection()) {
      setSubmitError('Please complete all required fields')
      return
    }

    setIsSubmitting(true)
    setSubmitError(null)
    recordSectionTime()

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.QUESTIONNAIRE_SUBMIT}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          total_time_seconds: (Date.now() - new Date(formData.time_started).getTime()) / 1000
        })
      })

      const data = await response.json()

      if (response.ok) {
        setSubmitSuccess(true)
        setTimeout(() => {
          navigate('/')
        }, 5000)
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

  // Success Screen
  if (submitSuccess) {
    return (
      <div className="research-questionnaire-page">
        <div className="success-container">
          <CheckCircle size={80} className="success-icon" />
          <h1>Thank You for Your Participation!</h1>
          <p className="success-message">
            Your responses have been successfully submitted and will contribute to advancing
            climate communication research.
          </p>
          <div className="success-details">
            <p><strong>Participant ID:</strong> {formData.participant_id}</p>
            <p>Please save this ID for your records.</p>
          </div>
          <p className="redirect-notice">Redirecting to home page in 5 seconds...</p>
        </div>
      </div>
    )
  }

  // Section Titles
  const sections = [
    { title: 'Consent & Demographics', icon: Users },
    { title: 'Your Recent Experience', icon: Target },
    { title: 'Task Success & Completion', icon: ClipboardCheck },
    { title: 'Document & Source Quality', icon: FileSearch },
    { title: 'User Experience (UEQ-S)', icon: TrendingUp },
    { title: 'Trust Evaluation', icon: CheckCircle },
    { title: 'Cognitive Load (NASA-TLX)', icon: Target },
    { title: 'Conversational Quality', icon: MessageCircle },
    { title: 'Feature-Specific Evaluation', icon: Target },
    { title: 'Source Transparency & Intentions', icon: ExternalLink },
    { title: 'Open Feedback', icon: MessageSquare }
  ]

  const SectionIcon = sections[currentSection].icon

  return (
    <div className="research-questionnaire-page">
      <div className="questionnaire-container">
        {/* Header */}
        <div className="questionnaire-header">
          <h1>NeuroClima Bot Research Study</h1>
          <p className="institution">University of Oulu Research Team | Estimated Time: 25 minutes</p>
        </div>

        {/* Progress Indicator */}
        <div className="progress-bar-container">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${((currentSection + 1) / sections.length) * 100}%` }}
            />
          </div>
          <p className="progress-text">
            Section {currentSection + 1} of {sections.length}: {sections[currentSection].title}
          </p>
        </div>

        {/* Section Steps */}
        <div className="section-steps">
          {sections.map((section, index) => (
            <div
              key={index}
              className={`step ${index === currentSection ? 'active' : ''} ${index < currentSection ? 'completed' : ''}`}
            >
              <div className="step-number">{index + 1}</div>
              <div className="step-label">{section.title}</div>
            </div>
          ))}
        </div>

        {/* Main Form */}
        <form onSubmit={handleSubmit} className="questionnaire-form">
          {/* SECTION 0: Consent & Demographics */}
          {currentSection === 0 && (
            <div className="form-section">
              <h2>Section 1: Informed Consent & Demographics</h2>
              <p className="section-description">
                Please review the study information and provide your consent and basic demographic information.
              </p>

              {/* Consent Information */}
              <div className="consent-box">
                <h3>Study Information</h3>
                <div className="info-grid">
                  <div className="research-info-item">
                    <strong>Study Title:</strong>
                    <p>{CONSENT_INFORMATION.study_title}</p>
                  </div>
                  <div className="research-info-item">
                    <strong>Institution:</strong>
                    <p>{CONSENT_INFORMATION.institution}</p>
                  </div>
                  <div className="research-info-item">
                    <strong>Purpose:</strong>
                    <p>{CONSENT_INFORMATION.purpose}</p>
                  </div>
                </div>

                <button
                  type="button"
                  className="btn-link"
                  onClick={() => setShowConsentDetails(!showConsentDetails)}
                >
                  <Info size={16} />
                  {showConsentDetails ? 'Hide' : 'Show'} Full Study Information
                </button>

                {showConsentDetails && (
                  <div className="consent-details">
                    <div className="detail-section">
                      <h4>Procedures</h4>
                      <pre>{CONSENT_INFORMATION.procedures}</pre>
                    </div>
                    <div className="detail-section">
                      <h4>Data Collected</h4>
                      <pre>{CONSENT_INFORMATION.data_collected}</pre>
                    </div>
                    <div className="detail-section">
                      <h4>Risks & Benefits</h4>
                      <pre>{CONSENT_INFORMATION.risks_benefits}</pre>
                    </div>
                    <div className="detail-section">
                      <h4>Confidentiality</h4>
                      <pre>{CONSENT_INFORMATION.confidentiality}</pre>
                    </div>
                    <div className="detail-section">
                      <h4>Voluntary Participation</h4>
                      <pre>{CONSENT_INFORMATION.voluntary}</pre>
                    </div>
                    <div className="detail-section">
                      <h4>Your GDPR Rights</h4>
                      <pre>{CONSENT_INFORMATION.gdpr_rights}</pre>
                    </div>
                    <div className="detail-section">
                      <h4>Contact Information</h4>
                      <pre>{CONSENT_INFORMATION.contact}</pre>
                    </div>
                  </div>
                )}
              </div>

              {/* Single Consent Checkbox */}
              <div className="consent-checkbox-container">
                <label className="consent-checkbox">
                  <input
                    type="checkbox"
                    checked={formData.consent_all}
                    onChange={(e) => handleInputChange('consent_all', e.target.checked)}
                    required
                  />
                  <span className="consent-text">
                    <strong>I have read and understood the study information above</strong>, and I voluntarily
                    consent to participate in this research study. I understand that:
                    <ul>
                      <li>I am 18 years or older</li>
                      <li>My participation is voluntary and I can withdraw at any time</li>
                      <li>My data will be anonymized and used for research purposes</li>
                      <li>My responses may be published in aggregated form in academic papers</li>
                      <li>I have the right to access, correct, or delete my data</li>
                    </ul>
                  </span>
                </label>
              </div>

              {/* Demographics */}
              <div className="demographics-section">
                <h3>Demographics</h3>
                <p className="required-note">* Required fields</p>

                <div className="form-row">
                  <div className="form-group">
                    <label>Email (optional, for follow-up only)</label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => handleInputChange('email', e.target.value)}
                      placeholder="your.email@example.com"
                    />
                    <small>Only used if you wish to be contacted about results</small>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Age Range *</label>
                    <select
                      value={formData.age_range}
                      onChange={(e) => handleInputChange('age_range', e.target.value)}
                      required
                    >
                      <option value="">Select...</option>
                      {DEMOGRAPHICS.age_ranges.map(option => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label>Education Level *</label>
                    <select
                      value={formData.education_level}
                      onChange={(e) => handleInputChange('education_level', e.target.value)}
                      required
                    >
                      <option value="">Select...</option>
                      {DEMOGRAPHICS.education_levels.map(option => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Country</label>
                    <input
                      type="text"
                      value={formData.country}
                      onChange={(e) => handleInputChange('country', e.target.value)}
                      placeholder="e.g., Italy, Greece, Portugal..."
                    />
                  </div>

                  <div className="form-group">
                    <label>Native Language *</label>
                    <select
                      value={formData.native_language}
                      onChange={(e) => handleInputChange('native_language', e.target.value)}
                      required
                    >
                      <option value="">Select...</option>
                      {DEMOGRAPHICS.languages.map(option => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Prior Climate Change Knowledge (self-rated)</label>
                    <div className="scale-selector">
                      {DEMOGRAPHICS.prior_knowledge_levels.map(level => (
                        <label key={level.value} className="scale-option">
                          <input
                            type="radio"
                            name="prior_climate_knowledge"
                            value={level.value}
                            checked={formData.prior_climate_knowledge === level.value}
                            onChange={() => handleInputChange('prior_climate_knowledge', level.value)}
                          />
                          <span className="scale-label">{level.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Experience with AI Chatbots (e.g., ChatGPT, Claude, etc.)</label>
                    <div className="scale-selector">
                      {DEMOGRAPHICS.ai_experience_levels.map(level => (
                        <label key={level.value} className="scale-option">
                          <input
                            type="radio"
                            name="prior_ai_experience"
                            value={level.value}
                            checked={formData.prior_ai_experience === level.value}
                            onChange={() => handleInputChange('prior_ai_experience', level.value)}
                          />
                          <span className="scale-label">{level.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 1: Your Recent Experience */}
          {currentSection === 1 && (
            <div className="form-section">
              <h2>Section 2: Your Recent Experience</h2>
              <p className="section-description">
                Tell us about how you used the NeuroClima chatbot.
              </p>

              <div className="form-group">
                <label>What was your primary purpose for using the chatbot? *</label>
                <select
                  value={formData.primary_purpose}
                  onChange={(e) => handleInputChange('primary_purpose', e.target.value)}
                  required
                >
                  <option value="">Select your primary purpose...</option>
                  {PRIMARY_PURPOSE_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>

              {formData.primary_purpose === 'other' && (
                <div className="form-group">
                  <label>Please specify: *</label>
                  <input
                    type="text"
                    value={formData.other_purpose}
                    onChange={(e) => handleInputChange('other_purpose', e.target.value)}
                    placeholder="Describe your primary purpose..."
                    required
                  />
                </div>
              )}

              <div className="form-group">
                <label>Which types of information-seeking tasks did you perform? * (Select all that apply)</label>
                <div className="checkbox-group">
                  {TASK_TYPES.map(task => (
                    <label key={task.value} className="checkbox-item">
                      <input
                        type="checkbox"
                        checked={formData.task_type.includes(task.value)}
                        onChange={() => handleTaskTypeToggle(task.value)}
                      />
                      <div>
                        <strong>{task.label}</strong>
                        <p className="task-description">{task.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div className="progress-indicator">
                Purpose: {formData.primary_purpose ? '✓' : '✗'} |
                Task Types: {formData.task_type.length} selected
              </div>
            </div>
          )}

          {/* SECTION 2: Task Success & Completion */}
          {currentSection === 2 && (
            <div className="form-section">
              <h2>Section 3: Task Success & Completion</h2>
              <p className="section-description">
                Please evaluate how well the chatbot helped you accomplish your goals.
              </p>

              <h3>Task Accomplishment</h3>
              <div className="likert-items">
                {TASK_SUCCESS_ITEMS.map((item, index) => (
                  <div key={item.id} className="form-group">
                    <label>{item.question}</label>
                    {item.type === 'single_choice' && (
                      <div className="radio-group">
                        {item.options.map(option => (
                          <label key={option.value} className="radio-item">
                            <input
                              type="radio"
                              name={item.id}
                              value={option.value}
                              checked={formData.task_success[item.id] === option.value}
                              onChange={() => handleNestedChange('task_success', item.id, option.value)}
                            />
                            <span>{option.label}</span>
                          </label>
                        ))}
                      </div>
                    )}
                    {item.type === 'likert_7' && (
                      <>
                        <div className="likert-scale">
                          {[1, 2, 3, 4, 5, 6, 7].map(value => (
                            <label key={value} className="likert-option">
                              <input
                                type="radio"
                                name={item.id}
                                value={value}
                                checked={formData.task_success[item.id] === value}
                                onChange={() => handleNestedChange('task_success', item.id, value)}
                              />
                              <span className="likert-value">{value}</span>
                            </label>
                          ))}
                        </div>
                        <div className="scale-labels">
                          <span className="label-left">{item.min_label}</span>
                          <span className="label-right">{item.max_label}</span>
                        </div>
                      </>
                    )}
                    {item.type === 'open_text' && (
                      <textarea
                        rows="3"
                        value={formData.task_success[item.id] || ''}
                        onChange={(e) => handleNestedChange('task_success', item.id, e.target.value)}
                        placeholder={item.placeholder}
                      />
                    )}
                  </div>
                ))}
              </div>

              <div className="divider"></div>

              <h3>Information Finding Effectiveness</h3>
              <div className="likert-items">
                {INFORMATION_FINDING_ITEMS.map((item, index) => (
                  <div key={item.id} className="likert-item">
                    <div className="item-number">{index + 1}</div>
                    <div className="item-statement">{item.statement}</div>
                    <div className="likert-scale">
                      {[1, 2, 3, 4, 5, 6, 7].map(value => (
                        <label key={value} className="likert-option">
                          <input
                            type="radio"
                            name={item.id}
                            value={value}
                            checked={formData.info_finding[item.id] === value}
                            onChange={() => handleNestedChange('info_finding', item.id, value)}
                          />
                          <span className="likert-value">{value}</span>
                        </label>
                      ))}
                    </div>
                    <div className="scale-labels">
                      <span className="label-left">{item.min_label}</span>
                      <span className="label-right">{item.max_label}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="progress-indicator">
                Task Success: {['task_accomplished', 'goal_satisfaction'].filter(f => formData.task_success[f] !== undefined).length} / 2 required |
                Information Finding: {Object.keys(formData.info_finding).length} / {INFORMATION_FINDING_ITEMS.length}
              </div>
            </div>
          )}

          {/* SECTION 3: Document & Source Quality */}
          {currentSection === 3 && (
            <div className="form-section">
              <h2>Section 4: Document & Source Quality</h2>
              <p className="section-description">
                Please evaluate the quality and usefulness of the documents and sources provided by the chatbot.
              </p>

              <h3>Document Quality</h3>
              <div className="likert-items">
                {DOCUMENT_QUALITY_ITEMS.map((item, index) => (
                  <div key={item.id} className="likert-item">
                    <div className="item-number">{index + 1}</div>
                    <div className="item-statement">{item.statement}</div>
                    <div className="likert-scale">
                      {[1, 2, 3, 4, 5, 6, 7].map(value => (
                        <label key={value} className="likert-option">
                          <input
                            type="radio"
                            name={item.id}
                            value={value}
                            checked={formData.doc_quality[item.id] === value}
                            onChange={() => handleNestedChange('doc_quality', item.id, value)}
                          />
                          <span className="likert-value">{value}</span>
                        </label>
                      ))}
                    </div>
                    <div className="scale-labels">
                      <span className="label-left">{item.min_label}</span>
                      <span className="label-right">{item.max_label}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="divider"></div>

              <h3>Information Adequacy</h3>
              <div className="likert-items">
                {INFORMATION_ADEQUACY_ITEMS.map((item, index) => (
                  <div key={item.id} className="form-group">
                    <label>{item.question}</label>
                    {item.type === 'single_choice' && (
                      <div className="radio-group">
                        {item.options.map(option => (
                          <label key={option.value} className="radio-item">
                            <input
                              type="radio"
                              name={item.id}
                              value={option.value}
                              checked={formData.info_adequacy[item.id] === option.value}
                              onChange={() => handleNestedChange('info_adequacy', item.id, option.value)}
                            />
                            <span>{option.label}</span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="progress-indicator">
                Document Quality: {Object.keys(formData.doc_quality).length} / {DOCUMENT_QUALITY_ITEMS.length} |
                Information Adequacy: {Object.keys(formData.info_adequacy).length} / {INFORMATION_ADEQUACY_ITEMS.length}
              </div>
            </div>
          )}

          {/* SECTION 4: UEQ-S (User Experience) */}
          {currentSection === 4 && (
            <div className="form-section">
              <h2>Section 5: User Experience Questionnaire (UEQ-S)</h2>
              <p className="section-description">
                Please rate your experience with the NeuroClima chatbot using the scales below.
                For each item, select the circle that best represents your impression.
              </p>

              <div className="ueq-items">
                {UEQ_S_ITEMS.map((item, index) => (
                  <div key={item.id} className="ueq-item">
                    <div className="item-number">{index + 1}</div>
                    <div className="semantic-differential">
                      <span className="left-anchor">{item.left_anchor}</span>
                      <div className="scale-points">
                        {[1, 2, 3, 4, 5, 6, 7].map(value => (
                          <label key={value} className="scale-point">
                            <input
                              type="radio"
                              name={item.id}
                              value={value}
                              checked={formData.ueq_s[item.id] === value}
                              onChange={() => handleNestedChange('ueq_s', item.id, value)}
                            />
                            <span className="point-marker">{value}</span>
                          </label>
                        ))}
                      </div>
                      <span className="right-anchor">{item.right_anchor}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="progress-indicator">
                Completed: {Object.keys(formData.ueq_s).length} / 8 items
              </div>
            </div>
          )}

          {/* SECTION 5: Trust Scale */}
          {currentSection === 5 && (
            <div className="form-section">
              <h2>Section 6: Trust in AI Evaluation</h2>
              <p className="section-description">
                Please rate your agreement with the following statements about the NeuroClima chatbot.
              </p>

              <div className="likert-items">
                {TRUST_SCALE_ITEMS.map((item, index) => (
                  <div key={item.id} className="likert-item">
                    <div className="item-number">{index + 1}</div>
                    <div className="item-statement">{item.statement}</div>
                    <div className="likert-scale">
                      {[1, 2, 3, 4, 5, 6, 7].map(value => (
                        <label key={value} className="likert-option">
                          <input
                            type="radio"
                            name={item.id}
                            value={value}
                            checked={formData.trust_scale[item.id] === value}
                            onChange={() => handleNestedChange('trust_scale', item.id, value)}
                          />
                          <span className="likert-value">{value}</span>
                        </label>
                      ))}
                    </div>
                    <div className="scale-labels">
                      <span className="label-left">{item.min_label}</span>
                      <span className="label-right">{item.max_label}</span>
                    </div>
                    <div className="dimension-badge">{item.dimension}</div>
                  </div>
                ))}
              </div>

              <div className="progress-indicator">
                Completed: {Object.keys(formData.trust_scale).length} / 12 items
              </div>
            </div>
          )}

          {/* SECTION 6: NASA-TLX */}
          {currentSection === 6 && (
            <div className="form-section">
              <h2>Section 7: Cognitive Load Assessment (NASA-TLX)</h2>
              <p className="section-description">
                Please rate the mental and physical demands of using the chatbot on a scale from 0 to 20.
              </p>

              <div className="tlx-items">
                {NASA_TLX_SUBSCALES.map((item, index) => (
                  <div key={item.id} className="tlx-item">
                    <div className="item-header">
                      <div className="item-number">{index + 1}</div>
                      <div className="item-question">{item.question}</div>
                    </div>
                    <div className="item-description">{item.description}</div>
                    <div className="slider-container">
                      <span className="slider-label left">{item.min_label}</span>
                      <input
                        type="range"
                        min="0"
                        max="20"
                        step="1"
                        value={formData.nasa_tlx[item.id] || 10}
                        onChange={(e) => handleNestedChange('nasa_tlx', item.id, parseInt(e.target.value))}
                        className="nasa-slider"
                      />
                      <span className="slider-label right">{item.max_label}</span>
                    </div>
                    <div className="slider-value">
                      Selected: <strong>{formData.nasa_tlx[item.id] || 10}</strong> / 20
                    </div>
                  </div>
                ))}
              </div>

              <div className="progress-indicator">
                Completed: {Object.keys(formData.nasa_tlx).length} / 6 subscales
              </div>
            </div>
          )}

          {/* SECTION 7: Conversational Quality */}
          {currentSection === 7 && (
            <div className="form-section">
              <h2>Section 8: Conversational Quality</h2>
              <p className="section-description">
                Please evaluate the quality of your conversational interactions with the chatbot.
              </p>

              <div className="likert-items">
                {CONVERSATIONAL_QUALITY_ITEMS.map((item, index) => (
                  <div key={item.id} className="likert-item">
                    <div className="item-number">{index + 1}</div>
                    <div className="item-statement">{item.statement}</div>
                    <div className="likert-scale">
                      {[1, 2, 3, 4, 5, 6, 7].map(value => (
                        <label key={value} className="likert-option">
                          <input
                            type="radio"
                            name={item.id}
                            value={value}
                            checked={formData.conversational_quality[item.id] === value}
                            onChange={() => handleNestedChange('conversational_quality', item.id, value)}
                          />
                          <span className="likert-value">{value}</span>
                        </label>
                      ))}
                    </div>
                    <div className="scale-labels">
                      <span className="label-left">{item.min_label}</span>
                      <span className="label-right">{item.max_label}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="progress-indicator">
                Completed: {Object.keys(formData.conversational_quality).length} / {CONVERSATIONAL_QUALITY_ITEMS.length} items
              </div>
            </div>
          )}

          {/* SECTION 8: Feature-Specific Evaluations (STP always present) */}
          {currentSection === 8 && (
            <div className="form-section">
              <h2>Section 9: Feature-Specific Evaluation</h2>
              <p className="section-description">
                Please evaluate specific features of the chatbot.
              </p>

              {/* STP Feature - Always present */}
              <div className="feature-section">
                <h3>Social Tipping Points (STP) Analysis</h3>
                <div className="info-box info">
                  <Info size={16} />
                  <p>Social Tipping Points information is automatically included in all chatbot responses.</p>
                </div>
                <div className="feature-evaluation">
                  {STP_EVALUATION_ITEMS.map((item, index) => (
                    <div key={item.id} className="likert-item">
                      <div className="item-number">{index + 1}</div>
                      <div className="item-statement">{item.statement}</div>
                      <div className="likert-scale">
                        {[1, 2, 3, 4, 5, 6, 7].map(value => (
                          <label key={value} className="likert-option">
                            <input
                              type="radio"
                              name={item.id}
                              value={value}
                              checked={formData.stp_evaluation[item.id] === value}
                              onChange={() => handleNestedChange('stp_evaluation', item.id, value)}
                            />
                            <span className="likert-value">{value}</span>
                          </label>
                        ))}
                      </div>
                      <div className="scale-labels">
                        <span className="label-left">{item.min_label}</span>
                        <span className="label-right">{item.max_label}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="divider"></div>

              {/* Knowledge Graph Visualization */}
              <div className="feature-section">
                <h3>Knowledge Graph Visualization</h3>
                <div className="yes-no-selector">
                  <label>Did you use the Knowledge Graph visualization feature?</label>
                  <div className="yn-options">
                    <label className="yn-option">
                      <input
                        type="radio"
                        name="used_kg_viz"
                        checked={formData.used_kg_viz === true}
                        onChange={() => handleInputChange('used_kg_viz', true)}
                      />
                      <span>Yes</span>
                    </label>
                    <label className="yn-option">
                      <input
                        type="radio"
                        name="used_kg_viz"
                        checked={formData.used_kg_viz === false}
                        onChange={() => handleInputChange('used_kg_viz', false)}
                      />
                      <span>No</span>
                    </label>
                  </div>
                </div>

                {formData.used_kg_viz && (
                  <div className="feature-evaluation">
                    {KG_VISUALIZATION_ITEMS.map((item, index) => (
                      <div key={item.id} className="likert-item">
                        <div className="item-number">{index + 1}</div>
                        <div className="item-statement">{item.statement}</div>
                        <div className="likert-scale">
                          {[1, 2, 3, 4, 5, 6, 7].map(value => (
                            <label key={value} className="likert-option">
                              <input
                                type="radio"
                                name={item.id}
                                value={value}
                                checked={formData.kg_visualization[item.id] === value}
                                onChange={() => handleNestedChange('kg_visualization', item.id, value)}
                              />
                              <span className="likert-value">{value}</span>
                            </label>
                          ))}
                        </div>
                        <div className="scale-labels">
                          <span className="label-left">{item.min_label}</span>
                          <span className="label-right">{item.max_label}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Multilingual Feature */}
              <div className="feature-section">
                <h3>Multilingual Support</h3>
                <div className="yes-no-selector">
                  <label>Did you use the chatbot in a language other than English?</label>
                  <div className="yn-options">
                    <label className="yn-option">
                      <input
                        type="radio"
                        name="used_non_english"
                        checked={formData.used_non_english === true}
                        onChange={() => handleInputChange('used_non_english', true)}
                      />
                      <span>Yes</span>
                    </label>
                    <label className="yn-option">
                      <input
                        type="radio"
                        name="used_non_english"
                        checked={formData.used_non_english === false}
                        onChange={() => handleInputChange('used_non_english', false)}
                      />
                      <span>No</span>
                    </label>
                  </div>
                </div>

                {formData.used_non_english && (
                  <div className="feature-evaluation">
                    {MULTILINGUAL_EVALUATION_ITEMS.map((item, index) => (
                      <div key={item.id} className="likert-item">
                        <div className="item-number">{index + 1}</div>
                        <div className="item-statement">{item.statement}</div>
                        <div className="likert-scale">
                          {[1, 2, 3, 4, 5, 6, 7].map(value => (
                            <label key={value} className="likert-option">
                              <input
                                type="radio"
                                name={item.id}
                                value={value}
                                checked={formData.multilingual[item.id] === value}
                                onChange={() => handleNestedChange('multilingual', item.id, value)}
                              />
                              <span className="likert-value">{value}</span>
                            </label>
                          ))}
                        </div>
                        <div className="scale-labels">
                          <span className="label-left">{item.min_label}</span>
                          <span className="label-right">{item.max_label}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* SECTION 9: Source Transparency & Behavioral Intentions */}
          {currentSection === 9 && (
            <div className="form-section">
              <h2>Section 10: Source Transparency & Future Intentions</h2>

              <h3>Source Transparency & Trust</h3>
              <p className="section-description">
                Please rate your agreement with these statements about the chatbot's sources and transparency.
              </p>

              <div className="likert-items">
                {RAG_TRANSPARENCY_ITEMS.map((item, index) => (
                  <div key={item.id} className="likert-item">
                    <div className="item-number">{index + 1}</div>
                    <div className="item-statement">{item.statement}</div>
                    <div className="likert-scale">
                      {[1, 2, 3, 4, 5, 6, 7].map(value => (
                        <label key={value} className="likert-option">
                          <input
                            type="radio"
                            name={item.id}
                            value={value}
                            checked={formData.rag_transparency[item.id] === value}
                            onChange={() => handleNestedChange('rag_transparency', item.id, value)}
                          />
                          <span className="likert-value">{value}</span>
                        </label>
                      ))}
                    </div>
                    <div className="scale-labels">
                      <span className="label-left">{item.min_label}</span>
                      <span className="label-right">{item.max_label}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="divider"></div>

              <h3>Behavioral Intentions</h3>
              <p className="section-description">
                Please indicate your agreement with the following statements about your future intentions.
              </p>

              <div className="likert-items">
                {BEHAVIORAL_INTENTIONS_ITEMS.map((item, index) => (
                  <div key={item.id} className="likert-item">
                    <div className="item-number">{index + 1}</div>
                    <div className="item-statement">{item.statement}</div>
                    <div className="likert-scale">
                      {[1, 2, 3, 4, 5, 6, 7].map(value => (
                        <label key={value} className="likert-option">
                          <input
                            type="radio"
                            name={item.id}
                            value={value}
                            checked={formData.behavioral_intentions[item.id] === value}
                            onChange={() => handleNestedChange('behavioral_intentions', item.id, value)}
                          />
                          <span className="likert-value">{value}</span>
                        </label>
                      ))}
                    </div>
                    <div className="scale-labels">
                      <span className="label-left">{item.min_label}</span>
                      <span className="label-right">{item.max_label}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="progress-indicator">
                Source Transparency: {Object.keys(formData.rag_transparency).length} / 5 |
                Behavioral Intentions: {Object.keys(formData.behavioral_intentions).length} / 5
              </div>
            </div>
          )}

          {/* SECTION 10: Open-Ended Feedback */}
          {currentSection === 10 && (
            <div className="form-section">
              <h2>Section 11: Open Feedback</h2>
              <p className="section-description">
                Finally, please share any additional thoughts or feedback (optional).
              </p>

              <div className="form-group">
                <label>What features did you find most useful?</label>
                <textarea
                  rows="4"
                  value={formData.most_useful_features}
                  onChange={(e) => handleInputChange('most_useful_features', e.target.value)}
                  placeholder="Describe the features you found most helpful..."
                />
              </div>

              <div className="form-group">
                <label>What improvements would you suggest?</label>
                <textarea
                  rows="4"
                  value={formData.suggested_improvements}
                  onChange={(e) => handleInputChange('suggested_improvements', e.target.value)}
                  placeholder="Share your ideas for improving the chatbot..."
                />
              </div>

              <div className="form-group">
                <label>Any additional comments?</label>
                <textarea
                  rows="4"
                  value={formData.additional_comments}
                  onChange={(e) => handleInputChange('additional_comments', e.target.value)}
                  placeholder="Any other thoughts you'd like to share..."
                />
              </div>

              <div className="info-box success">
                <CheckCircle size={20} />
                <p>
                  <strong>You're almost done!</strong> Click "Submit" below to complete the questionnaire.
                </p>
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
              onClick={handlePrevious}
              disabled={currentSection === 0}
            >
              <ChevronLeft size={18} />
              Previous
            </button>

            <div className="section-indicator">
              {currentSection + 1} / {sections.length}
            </div>

            {currentSection < sections.length - 1 ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleNext}
                disabled={!canProceedToNextSection()}
              >
                Next
                <ChevronRight size={18} />
              </button>
            ) : (
              <button
                type="submit"
                className="btn btn-success"
                disabled={!canProceedToNextSection() || isSubmitting}
              >
                {isSubmitting ? 'Submitting...' : 'Submit Questionnaire'}
                <CheckCircle size={18} />
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}

export default ResearchQuestionnaire
