"""
Centralized Prompt Templates for Document Processing

This file contains all prompts used for:
- Document summarization (research papers, policy, scientific data, news)
- Image/vision description (charts, diagrams, photos, tables)

All prompts are designed to generate flowing, paragraph-based outputs
without numbered sections or bullet points.
"""

# ============================================================================
# SUMMARIZATION PROMPTS
# ============================================================================
# All summarization prompts are designed to generate high-level, abstractive
# summaries in flowing paragraph form (1-2 paragraphs, 200-300 words).
# ============================================================================

RESEARCH_PAPER_SUMMARY_PROMPT = """Generate a concise, high-level abstractive summary of this research paper in flowing paragraph form. Write 1-2 well-structured paragraphs (200-300 words total) that capture the essence of the research.

Your summary should flow naturally and cover: the problem or gap being addressed, why it matters, the research approach and methodology used, the key findings and their significance, and the broader implications or contributions to the field. Write in a scholarly yet accessible tone, using complete sentences that connect ideas smoothly. Focus on synthesis rather than listing details.

Research Paper Content:
{content}

Write a comprehensive paragraph-based summary:"""

POLICY_DOCUMENT_SUMMARY_PROMPT = """Generate a concise, high-level abstractive summary of this policy document in flowing paragraph form. Write 1-2 well-structured paragraphs (200-300 words total) that capture the essence of the policy.

Your summary should flow naturally and cover: the problem or need the policy addresses, the policy's main objectives and scope, key provisions and mechanisms established, how it affects stakeholders, and its broader significance or implications. Write in clear, professional language that makes the policy accessible while preserving important context. Focus on synthesis rather than listing requirements.

Policy Document Content:
{content}

Write a comprehensive paragraph-based summary:"""

SCIENTIFIC_DATA_SUMMARY_PROMPT = """Generate a concise, high-level abstractive summary of this scientific dataset in flowing paragraph form. Write 1-2 well-structured paragraphs (200-300 words total) that capture the essence of the dataset.

Your summary should flow naturally and cover: what the dataset represents and its scientific context, why this data is important and what gap it fills, the types of measurements and observations included, how the data was collected, and its potential applications and scientific value. Write in precise, scientific language that makes the dataset's significance clear. Focus on synthesis rather than listing variables.

Scientific Data Content:
{content}

Write a comprehensive paragraph-based summary:"""

NEWS_SUMMARY_PROMPT = """Generate a concise, high-level abstractive summary of this news content in flowing paragraph form. Write 1-2 well-structured paragraphs (200-300 words total) that capture the essence of the story.

Your summary should flow naturally and cover: the main events or developments, the background and context that makes this newsworthy, key facts and perspectives from stakeholders, what this means for affected parties, and the broader significance or implications. Write in engaging, journalistic style that tells the complete story while maintaining objectivity. Focus on synthesis rather than listing facts.

News Content:
{content}

Write a comprehensive paragraph-based summary:"""

NEWS_INDIVIDUAL_ARTICLE_PROMPT = """Generate a concise, high-level abstractive summary of this news article in flowing paragraph form. Write 1-2 well-structured paragraphs (200-300 words total) that capture the essence of the article.

Article Title: {title}
Source: {source_info}

Your summary should flow naturally and cover: what happened and why it matters, the background and context, key facts and quotes from important figures, who is affected and how, and what this means for the broader situation. Write in clear, engaging style that captures the full story. Focus on synthesis rather than listing events.

Article Content:
{content}

Write a comprehensive paragraph-based summary:"""

NEWS_COLLECTION_SUMMARY_PROMPT = """Generate a concise, high-level abstractive synthesis of this news collection in flowing paragraph form. Write 1-2 well-structured paragraphs (200-300 words total) that identify overarching themes and significance.

Your synthesis should flow naturally and cover: the main themes and patterns across articles, how different pieces complement each other, the collective significance of these stories, and what broader narrative or situation they reveal. Rather than summarizing each article separately, weave together the common threads and emerging insights. Write in analytical style that presents a unified understanding.

News Collection Content:
{content}

Write a comprehensive paragraph-based synthesis:"""

DEFAULT_SUMMARY_PROMPT = """Generate a concise, high-level abstractive summary of this document in flowing paragraph form. Write 1-2 well-structured paragraphs (200-300 words total) that capture the essence of the content.

Your summary should flow naturally and cover: what the document is about and its purpose, the main themes and key information presented, important findings or arguments, and why this content matters or what significance it has. Write in clear, engaging prose that provides a complete understanding. Focus on synthesis rather than listing details.

Document Content:
{content}

Write a comprehensive paragraph-based summary:"""


# ============================================================================
# VISION/IMAGE DESCRIPTION PROMPTS
# ============================================================================
# All vision prompts are designed to generate detailed, comprehensive
# descriptions that can replace images in text-based processing.
# ============================================================================

GENERAL_IMAGE_DESCRIPTION_PROMPT = """Analyze this image from a scientific/research document and provide a comprehensive, detailed description in flowing paragraph form.

Write 2-3 well-structured paragraphs that cover: what type of image this is and what it depicts, all visible text and labels (transcribed exactly), the key visual elements and their significance, any data or quantitative information shown, the scientific or technical content conveyed, and the image's purpose within the document. Be thorough and specific, as this description will replace the image in text-based processing.

Provide your detailed description:"""

CHART_GRAPH_DESCRIPTION_PROMPT = """Analyze this chart, graph, or data visualization in detail and provide a comprehensive description in flowing paragraph form.

Write 2-3 well-structured paragraphs that cover: the type of visualization and its title, axis labels and scales with exact values, all data series shown with their trends and key data points, quantitative analysis including min/max values and patterns, any annotations or additional elements, and the key insights or story this visualization tells. Be precise with numbers and measurements.

Detailed chart description:"""

DIAGRAM_ILLUSTRATION_DESCRIPTION_PROMPT = """Analyze this diagram, illustration, or schematic and provide a detailed textual description in flowing paragraph form.

Write 2-3 well-structured paragraphs that cover: the type of diagram and its overall structure, all major components and elements with their labels, how elements are connected and what those connections represent, the process or system flow if applicable, any text annotations or special symbols used, and what concept or system this diagram explains. Be comprehensive so the description conveys the same information as the visual.

Detailed diagram description:"""

PHOTO_IMAGE_DESCRIPTION_PROMPT = """Analyze this photograph or realistic image and provide a detailed description in flowing paragraph form.

Write 2-3 well-structured paragraphs that cover: what type of photograph this is and its main subject, detailed visual elements including foreground and background, scale indicators and spatial relationships, any scientific or technical features visible, all visible text and labels transcribed exactly, the context and apparent purpose of the image, and its relevance to the document. Provide objective, factual descriptions of what is visible.

Detailed image description:"""

TABLE_DATA_DESCRIPTION_PROMPT = """Analyze this table or structured data display and provide a complete textual representation in flowing paragraph form.

Write 2-3 well-structured paragraphs that cover: the table's title and purpose, its structure including column and row headers, the types of data and measurements shown, key data points and patterns in the values, any summary statistics or highlighted information, annotations or special formatting used, and the main findings or conclusions this table supports. For small tables, transcribe key data; for large tables, focus on structure and significant values.

Detailed table description:"""


# ============================================================================
# CLIMATGPT-7B SPECIFIC CONFIGURATION
# ============================================================================

CLIMATEGPT_SYSTEM_PROMPT = """You are ClimateGPT, an AI assistant specialized in climate science, environmental policy, and sustainable agriculture. Generate comprehensive, accurate summaries that synthesize complex information into clear, flowing narratives. Focus on the broader context and significance while maintaining scientific precision."""

# Model-specific parameters for ClimateGPT-7B
CLIMATEGPT_GENERATION_CONFIG = {
    'temperature': 0.3,
    'top_p': 0.9,
    'top_k': 50,
    'max_new_tokens': 400,  # ~300 words
    'repetition_penalty': 1.1,
    'do_sample': True
}
