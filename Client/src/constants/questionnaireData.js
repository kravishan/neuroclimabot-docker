/**
 * University of Oulu Research Questionnaire Data
 * Validated measurement instruments for evaluating NeuroClima RAG chatbot
 */

// Your Recent Experience - What users used the bot for
export const PRIMARY_PURPOSE_OPTIONS = [
  { value: 'research_papers', label: 'Finding research papers' },
  { value: 'policy_documents', label: 'Understanding policy documents' },
  { value: 'news_articles', label: 'Getting latest news on climate topics' },
  { value: 'scientific_data', label: 'Accessing scientific data' },
  { value: 'general_climate', label: 'General climate information' },
  { value: 'conversational', label: 'Conversational interaction / General questions' },
  { value: 'other', label: 'Other' }
];

// Information-Seeking Task Types (Nielsen Norman Group)
export const TASK_TYPES = [
  {
    value: 'acquire',
    label: 'Acquire',
    description: 'Looking for specific facts or data'
  },
  {
    value: 'compare',
    label: 'Compare/Choose',
    description: 'Evaluating multiple sources or solutions'
  },
  {
    value: 'understand',
    label: 'Understand',
    description: 'Gaining comprehensive understanding of a topic'
  },
  {
    value: 'explore',
    label: 'Explore',
    description: 'Browsing and discovering information'
  }
];

// Task Success & Completion Items
export const TASK_SUCCESS_ITEMS = [
  {
    id: 'goal_satisfaction',
    question: 'How satisfied were you with achieving your goal?',
    type: 'likert_7',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Not at all satisfied',
    max_label: 'Completely satisfied'
  },
  {
    id: 'specific_goal',
    question: 'What specifically were you trying to accomplish?',
    type: 'open_text',
    placeholder: 'Please describe your main goal...'
  }
];

// Information Finding Success Items
export const INFORMATION_FINDING_ITEMS = [
  {
    id: 'info_found',
    statement: 'I found the information I was looking for',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'info_relevant',
    statement: 'The responses were relevant to my questions',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'info_accurate',
    statement: 'The information provided was accurate',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'info_complete',
    statement: 'The information was comprehensive enough for my needs',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// Document & Source Quality (ResQue-adapted)
export const DOCUMENT_QUALITY_ITEMS = [
  {
    id: 'doc_relevant',
    statement: 'The research papers/documents provided were relevant to my query',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'doc_verifiable',
    statement: 'I could verify the information using the provided sources',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// Information Adequacy
export const INFORMATION_ADEQUACY_ITEMS = [
  {
    id: 'source_quantity',
    question: 'The number of sources provided was:',
    type: 'single_choice',
    options: [
      { value: 'too_few', label: 'Too few' },
      { value: 'just_right', label: 'Just right' },
      { value: 'too_many', label: 'Too many' }
    ]
  }
];

// UEQ-S: User Experience Questionnaire - Short (8 items)
// Source: UEQ.ueqplus.ug.edu, validated in 30+ languages
// 7-point semantic differential scale
export const UEQ_S_ITEMS = [
  {
    id: 'ueq_1',
    dimension: 'pragmatic',
    left_anchor: 'obstructive',
    right_anchor: 'supportive',
    left_value: 1,
    right_value: 7
  },
  {
    id: 'ueq_2',
    dimension: 'pragmatic',
    left_anchor: 'complicated',
    right_anchor: 'easy',
    left_value: 1,
    right_value: 7
  },
  {
    id: 'ueq_3',
    dimension: 'pragmatic',
    left_anchor: 'inefficient',
    right_anchor: 'efficient',
    left_value: 1,
    right_value: 7
  },
  {
    id: 'ueq_4',
    dimension: 'pragmatic',
    left_anchor: 'confusing',
    right_anchor: 'clear',
    left_value: 1,
    right_value: 7
  },
  {
    id: 'ueq_5',
    dimension: 'hedonic',
    left_anchor: 'boring',
    right_anchor: 'exciting',
    left_value: 1,
    right_value: 7
  },
  {
    id: 'ueq_6',
    dimension: 'hedonic',
    left_anchor: 'not interesting',
    right_anchor: 'interesting',
    left_value: 1,
    right_value: 7
  },
  {
    id: 'ueq_7',
    dimension: 'hedonic',
    left_anchor: 'conventional',
    right_anchor: 'inventive',
    left_value: 1,
    right_value: 7
  },
  {
    id: 'ueq_8',
    dimension: 'hedonic',
    left_anchor: 'usual',
    right_anchor: 'leading edge',
    left_value: 1,
    right_value: 7
  }
];

// Human-AI Trust Scale (8 items)
// Source: ACM 2025 validation study
// 7-point Likert scale (1=Strongly Disagree, 7=Strongly Agree)
// Dimensions: Cognitive trust (2) + Affective trust (6)
export const TRUST_SCALE_ITEMS = [
  // Cognitive Trust (Performance-based)
  {
    id: 'trust_2',
    dimension: 'cognitive',
    statement: 'I can depend on the chatbot to give accurate answers',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_6',
    dimension: 'cognitive',
    statement: 'I trust the chatbot to handle complex climate questions',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  // Affective Trust (Emotional-based)
  {
    id: 'trust_7',
    dimension: 'affective',
    statement: 'I feel confident using this chatbot for climate questions',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_8',
    dimension: 'affective',
    statement: 'I feel comfortable relying on the chatbot for climate information',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_9',
    dimension: 'affective',
    statement: 'The chatbot seems to understand my information needs',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_10',
    dimension: 'affective',
    statement: 'I would recommend this chatbot to others seeking climate information',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_11',
    dimension: 'affective',
    statement: 'Using this chatbot makes me feel more informed about climate change',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_12',
    dimension: 'affective',
    statement: 'I feel the chatbot is transparent about its limitations',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// NASA-TLX: Task Load Index (5 subscales)
// Source: NASA official, 4400+ studies validation
// 21-point scale (0-20) for each dimension
export const NASA_TLX_SUBSCALES = [
  {
    id: 'tlx_mental',
    dimension: 'mental_demand',
    question: 'How mentally demanding was using the chatbot?',
    scale_min: 0,
    scale_max: 20,
    min_label: 'Very Low',
    max_label: 'Very High',
    description: 'Mental and perceptual activity required (e.g., thinking, deciding, remembering)'
  },
  {
    id: 'tlx_physical',
    dimension: 'physical_demand',
    question: 'How physically demanding was using the chatbot?',
    scale_min: 0,
    scale_max: 20,
    min_label: 'Very Low',
    max_label: 'Very High',
    description: 'Physical activity required (e.g., typing, clicking, scrolling)'
  },
  {
    id: 'tlx_performance',
    dimension: 'performance',
    question: 'How successful were you in finding the information you needed?',
    scale_min: 0,
    scale_max: 20,
    min_label: 'Perfect',
    max_label: 'Failure',
    description: 'Your satisfaction with your performance'
  },
  {
    id: 'tlx_effort',
    dimension: 'effort',
    question: 'How hard did you have to work to get the information you needed?',
    scale_min: 0,
    scale_max: 20,
    min_label: 'Very Low',
    max_label: 'Very High',
    description: 'Mental and physical effort required'
  },
  {
    id: 'tlx_frustration',
    dimension: 'frustration',
    question: 'How insecure, discouraged, irritated, stressed, or annoyed did you feel?',
    scale_min: 0,
    scale_max: 20,
    min_label: 'Very Low',
    max_label: 'Very High',
    description: 'Negative emotions during use'
  }
];

// Conversational Quality Items (NEW)
export const CONVERSATIONAL_QUALITY_ITEMS = [
  {
    id: 'conv_followup',
    statement: 'The bot understood my follow-up questions',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'conv_appropriate',
    statement: 'The bot responded appropriately to different types of questions',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'conv_tone',
    statement: 'The bot\'s tone was appropriate and helpful',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// RAG-Specific Trust & Transparency (Removed - not needed)
export const RAG_TRANSPARENCY_ITEMS = [];

// Behavioral Intentions Scale (Removed - not needed)
export const BEHAVIORAL_INTENTIONS_ITEMS = [];

// Social Tipping Points (STP) Evaluation (4 items)
// Note: STP is automatic in all responses
export const STP_EVALUATION_ITEMS = [
  {
    id: 'stp_1',
    statement: 'The Social Tipping Points information in responses was helpful',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'stp_2',
    statement: 'The 5 qualifying factors were clear and understandable',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'stp_3',
    statement: 'The STP analysis helped me understand social aspects of climate topics',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'stp_4',
    statement: 'I found the STP information valuable',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// Knowledge Graph Visualization Evaluation (2 items - conditional)
export const KG_VISUALIZATION_ITEMS = [
  {
    id: 'kg_viz_1',
    statement: 'The knowledge graph visualization helped me understand connections between climate concepts',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'kg_viz_4',
    statement: 'I successfully found the information I was looking for using the graph',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// Multilingual Experience Evaluation (3 items - conditional)
export const MULTILINGUAL_EVALUATION_ITEMS = [
  {
    id: 'multi_1',
    statement: 'The responses in my language were natural and accurate',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'multi_2',
    statement: 'I prefer using the chatbot in my native language versus English',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'multi_3',
    statement: 'The translation quality met my expectations',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// Demographics Options
export const DEMOGRAPHICS = {
  age_ranges: [
    { value: '18-24', label: '18-24 years' },
    { value: '25-34', label: '25-34 years' },
    { value: '35-44', label: '35-44 years' },
    { value: '45-54', label: '45-54 years' },
    { value: '55-64', label: '55-64 years' },
    { value: '65+', label: '65+ years' }
  ],
  education_levels: [
    { value: 'high_school', label: 'High School' },
    { value: 'some_college', label: 'Some College' },
    { value: 'bachelors', label: 'Bachelor\'s Degree' },
    { value: 'masters', label: 'Master\'s Degree' },
    { value: 'doctorate', label: 'Doctoral Degree' },
    { value: 'other', label: 'Other' }
  ],
  prior_knowledge_levels: [
    { value: 1, label: 'Very Limited' },
    { value: 2, label: 'Limited' },
    { value: 3, label: 'Moderate' },
    { value: 4, label: 'Good' },
    { value: 5, label: 'Very Good' },
    { value: 6, label: 'Expert' }
  ],
  ai_experience_levels: [
    { value: 1, label: 'Never used' },
    { value: 2, label: 'Rarely' },
    { value: 3, label: 'Occasionally' },
    { value: 4, label: 'Frequently' },
    { value: 5, label: 'Very Frequently' }
  ],
  languages: [
    { value: 'en', label: 'English' },
    { value: 'it', label: 'Italian (Italiano)' },
    { value: 'el', label: 'Greek (Ελληνικά)' },
    { value: 'pt', label: 'Portuguese (Português)' }
  ]
};

// Consent Information (EU GDPR Compliant)
export const CONSENT_INFORMATION = {
  study_title: 'NeuroClima Chatbot Evaluation',
  institution: 'University of Oulu Research Team',
  purpose: `This research evaluates how people interact with an AI-powered climate information chatbot. Your feedback will help us improve the system and contribute to research on climate communication and information retrieval.`,
  procedures: `You will:
1. Provide basic demographic information (2 min)
2. Answer questions about your recent experience using the chatbot (3 min)
3. Complete questionnaires evaluating task success and user experience (15 min)
4. Provide feedback on specific features (5 min)
Total time: Approximately 25 minutes`,
  data_collected: `We collect:
- Your responses to questionnaires (demographics, task success, user experience ratings)
- Interaction patterns (what you used the bot for, task types)
- Feature usage (which features you used)
- Anonymized session data
We do NOT collect personally identifiable information unless you voluntarily provide an email for follow-up.`,
  risks_benefits: `Risks: Minimal. You may spend time reflecting on your experience.
Benefits: You will contribute to research improving climate information access and AI-based communication tools.`,
  confidentiality: `Your data will be:
- Anonymized (no personal identifiers in research datasets)
- Stored securely on encrypted servers
- Used only for research purposes
- Potentially published in aggregated form in academic papers
- Retained according to research standards`,
  voluntary: `Participation is completely voluntary. You may:
- Withdraw at any time without penalty
- Skip any questions you prefer not to answer
- Request deletion of your data within 30 days`,
  contact: `For questions contact: University of Oulu Research Team
For ethics concerns contact: kavindu.ravishan@oulu.fi or prasasthy.balasubramanian@oulu.fi`,
  gdpr_rights: `Under EU GDPR, you have the right to:
- Access your data
- Request correction or deletion
- Withdraw consent
- Lodge a complaint with a supervisory authority`
};

// Legacy exports for backward compatibility (not used in new questionnaire)
export const MACK_12_ITEMS = [];
export const GUIDED_TASKS = [];
