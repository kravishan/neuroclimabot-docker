/**
 * CHI 2027 Research Questionnaire Data
 * Validated measurement instruments for evaluating NeuroClima RAG chatbot
 */

// MACK-12: Multidimensional Assessment of Climate Knowledge (12 items)
// Source: Validated in PLOS Climate 2025
// Dimensions: Greenhouse effect, Causes & consequences, Individual & collective solutions, Climate science
export const MACK_12_ITEMS = [
  {
    id: 'mack_1',
    dimension: 'greenhouse_effect',
    question: 'The greenhouse effect is caused by gases in the atmosphere that trap heat.',
    correct_answer: true,
    type: 'true_false'
  },
  {
    id: 'mack_2',
    dimension: 'greenhouse_effect',
    question: 'Carbon dioxide (CO₂) is the most abundant greenhouse gas in Earth\'s atmosphere.',
    correct_answer: false, // Water vapor is most abundant
    type: 'true_false'
  },
  {
    id: 'mack_3',
    dimension: 'causes',
    question: 'Human activities, particularly burning fossil fuels, are the primary cause of recent global warming.',
    correct_answer: true,
    type: 'true_false'
  },
  {
    id: 'mack_4',
    dimension: 'causes',
    question: 'Deforestation contributes to climate change by reducing CO₂ absorption.',
    correct_answer: true,
    type: 'true_false'
  },
  {
    id: 'mack_5',
    dimension: 'consequences',
    question: 'Climate change only affects polar regions and does not impact temperate zones.',
    correct_answer: false,
    type: 'true_false'
  },
  {
    id: 'mack_6',
    dimension: 'consequences',
    question: 'Rising sea levels are caused by both melting ice and thermal expansion of warming oceans.',
    correct_answer: true,
    type: 'true_false'
  },
  {
    id: 'mack_7',
    dimension: 'individual_solutions',
    question: 'Individual actions like reducing energy consumption can help mitigate climate change.',
    correct_answer: true,
    type: 'true_false'
  },
  {
    id: 'mack_8',
    dimension: 'individual_solutions',
    question: 'Recycling is more effective at reducing emissions than reducing overall consumption.',
    correct_answer: false, // Reducing consumption is more effective
    type: 'true_false'
  },
  {
    id: 'mack_9',
    dimension: 'collective_solutions',
    question: 'Transitioning to renewable energy sources is essential for limiting global warming.',
    correct_answer: true,
    type: 'true_false'
  },
  {
    id: 'mack_10',
    dimension: 'collective_solutions',
    question: 'International cooperation is necessary to effectively address climate change.',
    correct_answer: true,
    type: 'true_false'
  },
  {
    id: 'mack_11',
    dimension: 'climate_science',
    question: 'Climate scientists have reached a consensus that human activities are causing global warming.',
    correct_answer: true,
    type: 'true_false'
  },
  {
    id: 'mack_12',
    dimension: 'climate_science',
    question: 'Current climate models cannot reliably predict future temperature changes.',
    correct_answer: false, // Models have proven reliable
    type: 'true_false'
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

// Human-AI Trust Scale (12 items)
// Source: ACM 2025 validation study
// 7-point Likert scale (1=Strongly Disagree, 7=Strongly Agree)
// Dimensions: Cognitive trust (6) + Affective trust (6)
export const TRUST_SCALE_ITEMS = [
  // Cognitive Trust (Performance-based)
  {
    id: 'trust_1',
    dimension: 'cognitive',
    statement: 'The chatbot provides reliable climate information.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_2',
    dimension: 'cognitive',
    statement: 'I can depend on the chatbot to give accurate answers.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_3',
    dimension: 'cognitive',
    statement: 'The sources provided by the chatbot are credible.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_4',
    dimension: 'cognitive',
    statement: 'The chatbot demonstrates competence in climate topics.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_5',
    dimension: 'cognitive',
    statement: 'The responses are consistent with scientific consensus.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_6',
    dimension: 'cognitive',
    statement: 'I trust the chatbot to handle complex climate questions.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  // Affective Trust (Emotional-based)
  {
    id: 'trust_7',
    dimension: 'affective',
    statement: 'I feel confident using this chatbot for climate questions.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_8',
    dimension: 'affective',
    statement: 'I feel comfortable relying on the chatbot for climate information.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_9',
    dimension: 'affective',
    statement: 'The chatbot seems to understand my information needs.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_10',
    dimension: 'affective',
    statement: 'I would recommend this chatbot to others seeking climate information.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_11',
    dimension: 'affective',
    statement: 'Using this chatbot makes me feel more informed about climate change.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'trust_12',
    dimension: 'affective',
    statement: 'I feel the chatbot is transparent about its limitations.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// NASA-TLX: Task Load Index (6 subscales)
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
    id: 'tlx_temporal',
    dimension: 'temporal_demand',
    question: 'How hurried or rushed was the pace of using the chatbot?',
    scale_min: 0,
    scale_max: 20,
    min_label: 'Very Low',
    max_label: 'Very High',
    description: 'Time pressure felt during interactions'
  },
  {
    id: 'tlx_performance',
    dimension: 'performance',
    question: 'How successful were you in finding the information you needed?',
    scale_min: 0,
    scale_max: 20,
    min_label: 'Perfect',
    max_label: 'Failure',
    description: 'Your satisfaction with your performance (note: scale is reversed)'
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

// RAG-Specific Trust & Transparency (5 items)
// Source: IBM Research CHI 2025 paper on RAG trust
export const RAG_TRANSPARENCY_ITEMS = [
  {
    id: 'rag_trust_1',
    statement: 'The sources cited are relevant to the chatbot\'s responses.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'rag_trust_2',
    statement: 'I can verify the information using the provided sources.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'rag_trust_3',
    statement: 'The chatbot clearly indicates when it is uncertain or has limitations.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'rag_trust_4',
    statement: 'The quality of sources increases my trust in the responses.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'rag_trust_5',
    statement: 'Having access to multiple sources helps me evaluate response accuracy.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// Behavioral Intentions Scale (5 items)
// Source: Climate change behavior research
export const BEHAVIORAL_INTENTIONS_ITEMS = [
  {
    id: 'behavior_1',
    statement: 'I intend to change my behavior based on the information I learned.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'behavior_2',
    statement: 'I am more likely to discuss climate change with others after using this chatbot.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'behavior_3',
    statement: 'I plan to seek more information about climate solutions.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'behavior_4',
    statement: 'I feel more motivated to take action on climate change.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'behavior_5',
    statement: 'I would use this chatbot again for climate-related questions.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// Feature-Specific Evaluations

// Social Tipping Points (STP) Evaluation (4 items)
export const STP_EVALUATION_ITEMS = [
  {
    id: 'stp_1',
    statement: 'The Social Tipping Points analysis helped me understand social aspects of climate change.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'stp_2',
    statement: 'The 5 qualifying factors (intervention, feedbacks, support, social-ecological embedding, dynamics) were clear and useful.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'stp_3',
    statement: 'The STP information influenced my understanding of climate action pathways.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'stp_4',
    statement: 'I found the STP analysis credible and scientifically sound.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// Knowledge Graph Visualization Evaluation (5 items)
export const KG_VISUALIZATION_ITEMS = [
  {
    id: 'kg_viz_1',
    statement: 'The knowledge graph visualization helped me understand connections between climate concepts.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'kg_viz_2',
    statement: 'The graph was easy to navigate and explore.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'kg_viz_3',
    statement: 'The visualization increased my trust in the chatbot\'s responses.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'kg_viz_4',
    statement: 'I successfully found the information I was looking for using the graph.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'kg_viz_5',
    statement: 'I prefer having the visualization available versus text-only responses.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// Multilingual Experience Evaluation (3 items)
export const MULTILINGUAL_EVALUATION_ITEMS = [
  {
    id: 'multi_1',
    statement: 'The responses in my language were natural and accurate.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'multi_2',
    statement: 'I prefer using the chatbot in my native language versus English.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  },
  {
    id: 'multi_3',
    statement: 'The translation quality met my expectations.',
    scale_min: 1,
    scale_max: 7,
    min_label: 'Strongly Disagree',
    max_label: 'Strongly Agree'
  }
];

// Guided Task Questions
export const GUIDED_TASKS = [
  {
    id: 'task_1',
    type: 'factual',
    title: 'Factual Query Task',
    instruction: 'Ask the chatbot: "What causes sea level rise?"',
    suggested_query: 'What causes sea level rise?',
    evaluation: [
      {
        id: 'task_1_success',
        question: 'Did you successfully get an answer to this question?',
        type: 'yes_no'
      },
      {
        id: 'task_1_satisfaction',
        question: 'How satisfied were you with the response quality?',
        scale_min: 1,
        scale_max: 7,
        min_label: 'Not at all satisfied',
        max_label: 'Extremely satisfied'
      }
    ]
  },
  {
    id: 'task_2',
    type: 'exploratory',
    title: 'Exploratory Query Task',
    instruction: 'Ask the chatbot: "How can cities adapt to climate change?"',
    suggested_query: 'How can cities adapt to climate change?',
    evaluation: [
      {
        id: 'task_2_success',
        question: 'Did you successfully get an answer to this question?',
        type: 'yes_no'
      },
      {
        id: 'task_2_comprehensiveness',
        question: 'How comprehensive was the response?',
        scale_min: 1,
        scale_max: 7,
        min_label: 'Not comprehensive',
        max_label: 'Very comprehensive'
      }
    ]
  },
  {
    id: 'task_3',
    type: 'stp',
    title: 'Social Tipping Points Task',
    instruction: 'Ask the chatbot: "What social changes support climate action?" (with STP analysis enabled)',
    suggested_query: 'What social changes support climate action?',
    note: 'Please enable "Show Social Tipping Points" before asking this question.',
    evaluation: [
      {
        id: 'task_3_stp_shown',
        question: 'Did you see Social Tipping Points analysis in the response?',
        type: 'yes_no'
      }
    ]
  },
  {
    id: 'task_4',
    type: 'visualization',
    title: 'Knowledge Graph Exploration Task',
    instruction: 'Open the knowledge graph visualization for one of your previous queries.',
    note: 'Look for the "View Knowledge Graph" button in previous responses.',
    evaluation: [
      {
        id: 'task_4_viz_accessed',
        question: 'Were you able to access the knowledge graph visualization?',
        type: 'yes_no'
      }
    ]
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
  study_title: 'NeuroClima: Evaluating Multi-Source RAG for Climate Communication',
  institution: 'CHI 2027 Research Study',
  purpose: `This research evaluates how people interact with an AI-powered climate information chatbot that combines multiple information retrieval methods (vector search, knowledge graphs, and summaries) with social tipping point analysis.`,
  procedures: `You will:
1. Complete a brief pre-task climate knowledge assessment (3 min)
2. Interact with the NeuroClima chatbot by completing 4 guided tasks (10-15 min)
3. Complete post-task questionnaires evaluating your experience (8-10 min)
Total time: Approximately 25-30 minutes`,
  data_collected: `We collect:
- Your responses to questionnaires (demographics, knowledge assessments, user experience ratings)
- Interaction logs (queries, response times, features used)
- Anonymized session data
We do NOT collect personally identifiable information unless you voluntarily provide an email for follow-up.`,
  risks_benefits: `Risks: Minimal. You may spend time thinking about climate change.
Benefits: You will learn about climate science and contribute to research improving AI-based climate communication.`,
  confidentiality: `Your data will be:
- Anonymized (no personal identifiers in research datasets)
- Stored securely on encrypted servers
- Used only for research purposes
- Potentially published in aggregated form in academic papers
- Retained for 5 years per research standards`,
  voluntary: `Participation is completely voluntary. You may:
- Withdraw at any time without penalty
- Skip any questions you prefer not to answer
- Request deletion of your data within 30 days`,
  contact: `For questions contact: [Your Research Team Email]
For ethics concerns contact: [Ethics Board Email]`,
  gdpr_rights: `Under EU GDPR, you have the right to:
- Access your data
- Request correction or deletion
- Withdraw consent
- Lodge a complaint with a supervisory authority`
};
