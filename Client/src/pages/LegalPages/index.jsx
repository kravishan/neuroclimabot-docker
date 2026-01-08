import React, { useEffect } from 'react'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import './LegalPages.css'

export function PrivacyPolicy() {

  useDocumentTitle('Privacy Policy - NeuroClima Bot')

  // Scroll to top when component mounts
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="legal-pages">
      <div className="legal-container">
        <div className="legal-content">
          <h1>Privacy Policy</h1>
          <p><strong>Last updated:</strong> May 2025</p>
          <p><strong>Effective Date:</strong> May 2025</p>
          
          <h2>1. Introduction</h2>
          <p>
            NeuroClima ("we," "our," or "us") is committed to protecting your privacy and personal data. 
            This Privacy Policy explains how we collect, use, process, and protect your information when you 
            use our NeuroClima Bot service ("Service") in accordance with the General Data Protection 
            Regulation (GDPR) and other applicable data protection laws.
          </p>

          <h2>2. Data Controller</h2>
          <p>
            <strong>NeuroClimaBot</strong><br/>
            Email: info@neuroclimabot.com<br/>
          </p>

          <h2>3. Information We Collect</h2>
          
          <h3>3.1 Personal Data</h3>
          <p>We collect minimal personal data necessary for service provision:</p>
          <ul>
            <li><strong>Feedback Data:</strong> Information provided through our feedback forms (optional)</li>
            <li><strong>Contact Information:</strong> Email address when you contact us for support</li>
            {/* <li><strong>Technical Data:</strong> IP address, browser type, device information for security and performance</li> */}
          </ul>

          <h3>3.2 Usage Data (Anonymous)</h3>
          <p>We collect anonymous usage data to improve our service:</p>
          <ul>
            <li>Chat interactions and queries (anonymized)</li>
            <li>Response accuracy feedback</li>
            <li>System performance metrics</li>
            <li>Error logs and debugging information</li>
          </ul>

          <h3>3.3 Development Data (Testing Phase Only)</h3>
          <div className="important-notice">
            <p><strong>IMPORTANT NOTICE - TESTING PHASE:</strong></p>
            <p>
              During our current testing and development phase, we use LangSmith (by LangChain) to 
              monitor and improve our AI system. This service temporarily stores:
            </p>
            <ul>
              <li>User queries and bot responses (anonymized)</li>
              <li>Conversation flows and patterns</li>
              <li>Error tracking and performance metrics</li>
              <li>Prompt optimization data</li>
            </ul>
            <p>
              <strong>This data collection is:</strong>
            </p>
            <ul>
              <li>Anonymous (no personal identifiers)</li>
              <li>Used solely for development and testing purposes</li>
              <li>Stored securely with enterprise-grade encryption</li>
              <li>Will be deleted upon official project handover</li>
              <li>Not shared with third parties for commercial purposes</li>
            </ul>
            <p>
              <em>This testing-phase data collection will cease when the project transitions 
              from development to production status.</em>
            </p>
          </div>

          <h2>4. Legal Basis for Processing (GDPR Article 6)</h2>
          <ul>
            <li><strong>Legitimate Interest:</strong> Service improvement, security, and technical support</li>
            <li><strong>Consent:</strong> Feedback forms and voluntary communications</li>
            <li><strong>Contractual Necessity:</strong> Service provision and user support</li>
          </ul>

          <h2>5. How We Use Your Information</h2>
          <ul>
            <li>Provide and maintain the NeuroClima Bot service</li>
            <li>Improve AI model accuracy and performance</li>
            <li>Ensure system security and prevent misuse</li>
            <li>Respond to user feedback and support requests</li>
            <li>Comply with legal obligations</li>
            <li>Debug errors and optimize system performance</li>
          </ul>

          <h2>6. Data Sharing and Third Parties</h2>
          <p>We do not sell or commercially share your personal data. Limited sharing occurs for:</p>
          <ul>
            <li><strong>LangSmith (Testing Phase):</strong> Anonymous development data only</li>
            <li><strong>Cloud Infrastructure:</strong> Secure hosting and data processing</li>
            <li><strong>Legal Requirements:</strong> When required by law or legal process</li>
          </ul>

          <h2>7. Your Rights Under GDPR</h2>
          <p>You have the following rights regarding your personal data:</p>
          <ul>
            <li><strong>Right of Access:</strong> Request information about your data</li>
            <li><strong>Right to Rectification:</strong> Correct inaccurate data</li>
            <li><strong>Right to Erasure:</strong> Request deletion of your data</li>
            <li><strong>Right to Restrict Processing:</strong> Limit how we use your data</li>
            <li><strong>Right to Data Portability:</strong> Receive your data in structured format</li>
            <li><strong>Right to Object:</strong> Object to processing based on legitimate interest</li>
            <li><strong>Right to Withdraw Consent:</strong> For consent-based processing</li>
          </ul>
          <p>To exercise these rights, contact us at: <strong>info@neuroclimabot.com</strong></p>

          <h2>8. Data Security</h2>
          <p>We implement industry-standard security measures:</p>
          <ul>
            <li>End-to-end encryption for data transmission</li>
            <li>Secure cloud infrastructure with access controls</li>
            <li>Regular security audits and vulnerability assessments</li>
            <li>Staff training on data protection principles</li>
          </ul>

          <h2>10. International Data Transfers</h2>
          <p>
            Data may be processed in the EU/EEA and other countries with adequate protection levels. 
            All transfers comply with GDPR requirements and include appropriate safeguards.
          </p>

          <h2>11. Changes to This Policy</h2>
          <p>
            We may update this Privacy Policy to reflect changes in our practices or legal requirements. 
            Material changes will be communicated with at least 30 days notice.
          </p>

          <h2>12. Contact and Complaints</h2>
          <p>
            <strong>General Support:</strong> info@neuroclimabot.com
          </p>
          <p>
            You have the right to lodge a complaint with your local data protection authority 
            if you believe your rights have been violated.
          </p>
        </div>
      </div>
    </div>
  );
}

export function Disclaimer() {
  useDocumentTitle('Disclaimer - NeuroClima Bot')

  // Scroll to top when component mounts
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="legal-pages">
      <div className="legal-container">
        <h1>Disclaimer</h1>
        <p><strong>Last updated:</strong> May 2025</p>

        <h2>1. General Information Disclaimer</h2>
        <p>
          The NeuroClima Bot service ("Service") provides AI-generated information about 
          climate policy and environmental topics for informational and educational purposes only. 
          The information provided should not be considered as professional advice, legal counsel, 
          or authoritative policy guidance.
        </p>

        <h2>2. AI-Generated Content Limitations</h2>
        <div className="important-notice">
          <p><strong>IMPORTANT:</strong> NeuroClima Bot is an artificial intelligence system that can make mistakes.</p>
          <ul>
            <li> <strong>Always verify</strong> important information from official sources</li>
            <li> <strong>Cross-reference</strong> critical data before making decisions</li>
            <li> <strong>Consult experts</strong> for professional advice</li>
            <li> <strong>Do not rely solely</strong> on AI-generated content for critical decisions</li>
          </ul>
        </div>

        <h2>3. No Professional Advice</h2>
        <p>
          The Service does not provide and should not be construed as providing:
        </p>
        <ul>
          <li>Legal advice or legal interpretation</li>
          <li>Professional policy consulting</li>
          <li>Investment or financial guidance</li>
          <li>Scientific research conclusions</li>
          <li>Official government positions or policies</li>
        </ul>

        <h2>4. Accuracy and Reliability</h2>
        <p>
          While we strive to provide accurate and up-to-date information:
        </p>
        <ul>
          <li>We do not guarantee the accuracy, completeness, or reliability of any information</li>
          <li>Information may become outdated as policies and regulations change</li>
          <li>AI-generated responses may contain errors or inaccuracies</li>
          <li>Source documents may have limitations or biases</li>
        </ul>

        <h2>5. External Links and Third-Party Content</h2>
        <p>
          Our Service may contain links to external websites or reference third-party content:
        </p>
        <ul>
          <li>We are not responsible for the content, accuracy, or practices of external sites</li>
          <li>External links are provided for convenience and do not constitute endorsement</li>
          <li>Third-party content is subject to their respective terms and privacy policies</li>
        </ul>

        <h2>6. Service Availability</h2>
        <p>
          We do not guarantee:
        </p>
        <ul>
          <li>Continuous, uninterrupted service availability</li>
          <li>Error-free operation of the Service</li>
          <li>Compatibility with all devices or browsers</li>
          <li>Preservation of all data or conversations</li>
        </ul>

        <h2>7. User Responsibility</h2>
        <p>
          Users are responsible for:
        </p>
        <ul>
          <li>Verifying information before acting upon it</li>
          <li>Using the Service in compliance with applicable laws</li>
          <li>Respecting intellectual property rights</li>
          <li>Not misusing the Service for harmful purposes</li>
        </ul>

        <h2>8. Limitation of Liability</h2>
        <p>
          To the fullest extent permitted by law, NeuroClima Bot shall not be liable for any:
        </p>
        <ul>
          <li>Direct, indirect, incidental, or consequential damages</li>
          <li>Loss of profits, data, or business opportunities</li>
          <li>Decisions made based on AI-generated information</li>
          <li>Technical issues or service interruptions</li>
        </ul>

        <h2>9. Updates and Changes</h2>
        <p>
          This disclaimer may be updated periodically. Continued use of the Service 
          constitutes acceptance of any changes. Material changes will be communicated appropriately.
        </p>

        <h2>10. Contact Information</h2>
        <p>
          For questions about this disclaimer:<br/>
          <strong>Email:</strong> info@neuroclimabot.com<br/>
        </p>
      </div>
    </div>
  );
}

export function TermsOfUse() {
  useDocumentTitle('Terms of Use - NeuroClima Bot')

  // Scroll to top when component mounts
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="legal-pages">
      <div className="legal-container">
        <h1>Terms of Use</h1>
        <p><strong>Last updated:</strong> May 2025</p>
        <p><strong>Effective Date:</strong> May 2025</p>

        <h2>1. Agreement to Terms</h2>
        <p>
          By accessing or using the NeuroClima Bot service ("Service"), you agree to be bound by 
          these Terms of Use ("Terms"). If you do not agree to these Terms, you may not use the Service.
        </p>

        <h2>2. Description of Service</h2>
        <p>
          NeuroClima Bot is an AI-powered conversational service that provides information about 
          climate policy and environmental topics. The Service is currently in testing phase and 
          may be subject to changes, improvements, and updates.
        </p>

        <h2>3. Eligibility and Account Requirements</h2>
        <ul>
          <li>You must be at least 16 years old to use this Service</li>
          <li>You must comply with all applicable laws and regulations</li>
          <li>You are responsible for maintaining the security of your sessions</li>
          <li>One person may not maintain multiple accounts simultaneously</li>
        </ul>

        <h2>4. Acceptable Use Policy</h2>
        
        <h3>4.1 Permitted Uses</h3>
        <ul>
          <li>Research and educational purposes related to climate and environment</li>
          <li>General information gathering on climate policies</li>
          <li>Academic and professional development</li>
        </ul>

        <h3>4.2 Prohibited Uses</h3>
        <p>You agree NOT to use the Service to:</p>
        <ul>
          <li>Generate misleading or false climate information</li>
          <li>Attempt to reverse engineer or extract proprietary algorithms</li>
          <li>Overload or disrupt the Service infrastructure</li>
          <li>Collect personal data from other users</li>
          <li>Engage in harassment, abuse, or discriminatory behavior</li>
          <li>Violate any applicable laws or regulations</li>
          <li>Infringe on intellectual property rights</li>
          <li>Attempt to gain unauthorized access to systems</li>
        </ul>

        <h2>5. Intellectual Property Rights</h2>
        
        <h3>5.1 Our Rights</h3>
        <ul>
          <li>NeuroClima Bot retains all rights to the Service, technology, and platform</li>
          <li>AI model, algorithms, and proprietary technology remain our property</li>
          <li>Service trademarks, logos, and branding are protected</li>
        </ul>

        <h3>5.2 User Content</h3>
        <ul>
          <li>You retain ownership of content you input into the Service</li>
          <li>You grant us license to use your input for Service improvement (anonymized)</li>
          <li>You are responsible for ensuring you have rights to any content you submit</li>
        </ul>

        <h2>6. Privacy and Data Collection</h2>
        <p>
          Your privacy is governed by our Privacy Policy, which is incorporated by reference. 
          Key points:
        </p>
        <ul>
          <li>We collect minimal personal data necessary for service provision</li>
          <li>Anonymous usage data helps improve the AI system</li>
          <li>Testing-phase data (via LangFuse) is temporary and will be deleted</li>
          <li>You have rights under GDPR and applicable privacy laws</li>
        </ul>

        <h2>7. Service Availability and Modifications</h2>
        <ul>
          <li>We strive for high availability but cannot guarantee 100% uptime</li>
          <li>The Service may be temporarily unavailable for maintenance</li>
          <li>We reserve the right to modify, update, or discontinue features</li>
          <li>Beta/testing features may be changed or removed without notice</li>
        </ul>

        <h2>8. User Responsibilities</h2>
        <ul>
          <li>Verify important information from authoritative sources</li>
          <li>Use the Service responsibly and ethically</li>
          <li>Respect other users and community guidelines</li>
          <li>Report any bugs, errors, or security issues promptly</li>
          <li>Comply with all applicable laws in your jurisdiction</li>
        </ul>

        <h2>9. Disclaimers and Limitations</h2>
        <ul>
          <li>The Service is provided "as is" without warranties</li>
          <li>AI-generated content may contain errors or inaccuracies</li>
          <li>We are not liable for decisions made based on Service output</li>
          <li>Users assume responsibility for verifying information</li>
        </ul>

        <h2>10. Indemnification</h2>
        <p>
          You agree to indemnify and hold NeuroClima Bot harmless from any claims, damages, 
          or expenses arising from your use of the Service, violation of these Terms, 
          or infringement of any rights.
        </p>

        <h2>11. Termination</h2>
        
        <h3>11.1 Termination by You</h3>
        <ul>
          <li>You may stop using the Service at any time</li>
          <li>Contact us to request data deletion under GDPR</li>
        </ul>

        <h3>11.2 Termination by Us</h3>
        <ul>
          <li>We may suspend access for Terms violations</li>
          <li>We may discontinue the Service with reasonable notice</li>
          <li>Serious violations may result in immediate termination</li>
        </ul>

        <h2>12. Governing Law and Jurisdiction</h2>
        <p>
          These Terms are governed by the laws of the European Union and the jurisdiction 
          where NeuroClima Bot is established. Any disputes will be resolved through the 
          appropriate courts or alternative dispute resolution mechanisms.
        </p>

        <h2>13. Changes to Terms</h2>
        <ul>
          <li>We may update these Terms periodically</li>
          <li>Material changes will be communicated with at least 30 days notice</li>
          <li>Continued use constitutes acceptance of updated Terms</li>
          <li>You may terminate your use if you disagree with changes</li>
        </ul>

        <h2>14. Severability</h2>
        <p>
          If any provision of these Terms is found invalid or unenforceable, 
          the remaining provisions will continue in full force and effect.
        </p>

        <h2>15. Contact Information</h2>
        <p>
          <strong>General Inquiries:</strong> info@neuroclimabot.com<br/>
        </p>

        <p><em>These Terms constitute the complete agreement between you and NeuroClima Bot regarding the Service.</em></p>
      </div>
    </div>
  );
}

export function LearnMore() {
  useDocumentTitle('Learn More - NeuroClima Bot')
  
  // Scroll to top when component mounts
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="legal-pages">
      <div className="legal-container">
        <h1>Learn More About NeuroClima Bot</h1>
        
        <div className="important-notice">
          <p><strong>⚠️ Important Reminder:</strong></p>
          <p>
            NeuroClima Bot is an AI system that can make mistakes. Always verify important 
            information from authoritative sources before making decisions.
          </p>
        </div>

        <h2>1. How NeuroClima Bot Works</h2>
        <p>
          NeuroClima Bot is an advanced AI system that combines multiple technologies to provide 
          information about climate policy and environmental topics:
        </p>
        
        <h3>1.1 Core Technology</h3>
        <ul>
          <li><strong>Large Language Models (LLMs):</strong> Advanced AI models trained on diverse text data</li>
          <li><strong>Retrieval-Augmented Generation (RAG):</strong> Combines knowledge retrieval with AI generation</li>
          <li><strong>Vector Search:</strong> Finds relevant information from our climate policy database</li>
          <li><strong>Conversational Memory:</strong> Remembers context within your session</li>
        </ul>

        <h3>1.2 Information Sources</h3>
        <p>Our bot draws information from:</p>
        <ul>
          <li>Climate policy documents and research papers</li>
          <li>Environmental regulations and guidelines</li>
          <li>Scientific publications and reports</li>
          <li>Government and institutional publications</li>
          <li>International climate agreements and frameworks</li>
        </ul>

        <h2>2. Capabilities and Features</h2>
        
        <h3>2.1 What the Bot Can Do</h3>
        <ul>
          <li> Answer questions about climate policies and regulations</li>
          <li> Explain environmental concepts and frameworks</li>
          <li> Provide information on climate science and impacts</li>
          <li> Discuss sustainability practices and solutions</li>
          <li> Support multiple languages (English, Italian, Portuguese, Greek)</li>
          <li> Maintain conversation context throughout your session</li>
          <li> Provide source references for its information</li>
        </ul>

        <h3>2.2 Current Limitations</h3>
        <ul>
          <li> Cannot provide real-time or live data</li>
          <li> May not have the most recent policy updates</li>
          <li> Cannot provide legal advice or professional consulting</li>
          <li> May occasionally generate incorrect or incomplete information</li>
          <li> Cannot access external websites or current internet data</li>
          <li> Cannot remember conversations across different sessions</li>
        </ul>

        <h2>3. Best Practices for Using NeuroClima Bot</h2>
        
        <h3>3.1 Getting the Best Results</h3>
        <ul>
          <li><strong>Be Specific:</strong> Ask clear, detailed questions for better responses</li>
          <li><strong>Provide Context:</strong> Mention relevant location, timeframe, or scope</li>
          <li><strong>Follow Up:</strong> Ask clarifying questions if you need more detail</li>
          <li><strong>Check Sources:</strong> Review the provided source references</li>
        </ul>

        <h3>3.2 Verification Guidelines</h3>
        <div className="verification-box">
          <p><strong>Always verify information when:</strong></p>
          <ul>
            <li>Making policy or business decisions</li>
            <li>Writing reports or academic papers</li>
            <li>Seeking legal or regulatory compliance guidance</li>
            <li>Planning investments or strategic initiatives</li>
            <li>The information seems surprising or contradictory</li>
          </ul>
        </div>

        <h2>4. Development and Testing Phase</h2>
        <p>
          NeuroClima Bot is currently in an active development and testing phase:
        </p>
        
        <h3>4.1 What This Means</h3>
        <ul>
          <li>Features and responses are continuously being improved</li>
          <li>You may occasionally encounter bugs or unusual responses</li>
          <li>The system learns from interactions to become more accurate</li>
          <li>New capabilities are regularly added and tested</li>
        </ul>

        <h3>4.2 Data Collection for Improvement</h3>
        <p>
          During this testing phase, we collect anonymous data to improve the system:
        </p>
        <ul>
          <li>Conversation patterns and common question types</li>
          <li>Response accuracy and user satisfaction</li>
          <li>System errors and technical issues</li>
          <li>Performance metrics and optimization data</li>
        </ul>
        <p>
          <em>This data is anonymized and will be deleted when the project moves to production.</em>
        </p>

        <h2>5. Reporting Issues and Providing Feedback</h2>
        
        <h3>5.1 What to Report</h3>
        <p>Please help us improve by reporting:</p>
        <ul>
          <li><strong>Factual Errors:</strong> Incorrect information in responses</li>
          <li><strong>Technical Issues:</strong> System errors or unexpected behavior</li>
          <li><strong>Response Quality:</strong> Unclear or unhelpful answers</li>
          <li><strong>Missing Information:</strong> Gaps in knowledge or coverage</li>
        </ul>

        <h3>5.2 How to Provide Feedback</h3>
        <ul>
          <li>Use the thumbs up/down buttons after each response</li>
          <li>Contact our support team with detailed feedback</li>
          <li>Report specific errors with context and examples</li>
          <li>Suggest improvements or new features</li>
        </ul>

        <h2>6. Privacy and Data Protection</h2>
        <p>
          We take your privacy seriously:
        </p>
        <ul>
          <li>Conversations are not linked to personal identities</li>
          <li>We collect minimal data necessary for service improvement</li>
          <li>All data handling complies with GDPR and privacy regulations</li>
          <li>You have control over your data and can request deletion</li>
        </ul>

        <h2>7. Future Developments</h2>
        <p>
          We're continuously working to improve NeuroClima Bot with:
        </p>
        <ul>
          <li>Enhanced accuracy and knowledge coverage</li>
          <li>Real-time data integration capabilities</li>
          <li>Additional language support</li>
          <li>Specialized features for different user types</li>
          <li>Integration with external climate databases</li>
        </ul>

        <h2>8. Contact and Support</h2>
        <p>
          <strong>General Questions:</strong> info@neuroclimabot.com<br/>
        </p>

        <p>
          <em>
            Thank you for helping us improve NeuroClima Bot during this testing phase. 
            Your feedback and participation are essential to building a better tool for 
            climate policy and environmental information.
          </em>
        </p>
      </div>
    </div>
  );
}