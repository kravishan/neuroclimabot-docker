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
          <p><strong>Last updated:</strong> January 12, 2026</p>
          <p><strong>Effective Date:</strong> January 12, 2026</p>

          <h2>1. Introduction</h2>
          <p>
            NeuroClima ("we," "our," or "us") is committed to protecting your privacy and personal data.
            This Privacy Policy explains how we collect, use, process, and protect your information when you
            use our NeuroClima Bot service ("Service") in accordance with the General Data Protection
            Regulation (EU) 2016/679 ("GDPR") and other applicable data protection laws.
          </p>
          <p>
            <strong>We implement a privacy-by-design approach with user consent management, allowing you
            full control over your data collection preferences.</strong>
          </p>

          <h2>2. Data Controller</h2>
          <p>
            <strong>NeuroClimaBot</strong><br/>
            Email: info@bot.neuroclima.eu<br/>
          </p>

          <h2>3. Your Consent and Data Collection</h2>

          <h3>3.1 Consent Management (GDPR Article 7)</h3>
          <p>
            We implement a <strong>transparent consent management system</strong> that gives you full control
            over data collection. Upon your first visit, you will be presented with consent options:
          </p>
          <ul>
            <li><strong>Essential Functions:</strong> Required for basic service operation (cannot be disabled)</li>
            <li><strong>Analytics & Research:</strong> Optional data collection for system improvement and training</li>
          </ul>
          <p>
            <strong>Opt-out Model:</strong> Analytics and research data collection is enabled by default,
            but you can opt-out at any time through the Privacy Settings accessible via the Privacy button in the header.
          </p>

          <h3>3.2 Essential Data (Always Collected - GDPR Article 6(1)(b))</h3>
          <p>
            <strong>Legal Basis:</strong> Contractual necessity for service provision
          </p>
          <ul>
            <li><strong>Session Management:</strong> Temporary session IDs stored in your browser (no server storage)</li>
            <li><strong>Conversation Context:</strong> Current session messages for contextual responses</li>
            <li><strong>Language Preferences:</strong> Your selected language for response delivery</li>
          </ul>
          <p>
            <strong>Important:</strong> Essential data is <strong>never</strong> linked to your personal identity.
            All data is <strong>completely anonymized</strong> and cannot be traced back to you.
          </p>

          <h3>3.3 Analytics & Research Data (Optional - GDPR Article 6(1)(a))</h3>
          <p>
            <strong>Legal Basis:</strong> Your explicit consent (opt-out model)
          </p>
          <p>
            If you consent to analytics data collection, we use <strong>Langfuse</strong> (an observability
            platform) to collect anonymized interaction traces for:
          </p>
          <ul>
            <li><strong>AI Model Training:</strong> Improving response accuracy and relevance</li>
            <li><strong>System Monitoring:</strong> Identifying errors and performance bottlenecks</li>
            <li><strong>Quality Assurance:</strong> Evaluating response quality and user satisfaction</li>
            <li><strong>Research & Development:</strong> Advancing climate AI technology</li>
          </ul>

          <div className="important-notice">
            <p><strong>GDPR-COMPLIANT DATA COLLECTION:</strong></p>
            <ul>
              <li><strong>Completely Anonymous:</strong> No personal identifiers, IP addresses, or user tracking</li>
              <li><strong>User Control:</strong> Disable analytics anytime via Privacy Settings</li>
              <li><strong>Transparent Processing:</strong> Clear information about what data is collected and why</li>
              <li><strong>Consent Versioning:</strong> Your consent preferences are tracked with timestamps</li>
              <li><strong>Platform Independence:</strong> NeuroClima Bot data is separate from main platform</li>
              <li><strong>No Third-Party Sharing:</strong> Data never sold or shared for commercial purposes</li>
            </ul>
          </div>

          <h3>3.4 What We DO NOT Collect</h3>
          <p>To ensure your privacy, we explicitly <strong>do not collect:</strong></p>
          <ul>
            <li>Names, email addresses, or contact information (unless you voluntarily provide via support)</li>
            <li>IP addresses or geolocation data</li>
            <li>Device fingerprints or tracking cookies</li>
            <li>Cross-platform user tracking or profiling</li>
            <li>Authentication credentials or account information</li>
            <li>Payment or financial information</li>
          </ul>

          <h2>4. Legal Basis for Processing (GDPR Article 6)</h2>
          <p>We process data under the following legal bases:</p>
          <ul>
            <li><strong>Consent (Article 6(1)(a)):</strong> Analytics & Research data collection (opt-out model)</li>
            <li><strong>Contractual Necessity (Article 6(1)(b)):</strong> Essential service functions and session management</li>
            <li><strong>Legitimate Interest (Article 6(1)(f)):</strong> System security, fraud prevention, and service improvement</li>
            <li><strong>Legal Obligation (Article 6(1)(c)):</strong> Compliance with applicable EU and national laws</li>
          </ul>

          <h2>5. How We Use Your Information</h2>
          <p>We use collected data strictly for the following purposes:</p>

          <h3>5.1 Essential Service Operations</h3>
          <ul>
            <li>Provide conversational AI responses to your climate-related questions</li>
            <li>Maintain conversation context within active sessions</li>
            <li>Deliver responses in your preferred language</li>
            <li>Ensure basic system functionality and security</li>
          </ul>

          <h3>5.2 Analytics & Research (Only with Your Consent)</h3>
          <ul>
            <li>Train and improve AI models for better response accuracy</li>
            <li>Monitor system performance and identify technical issues</li>
            <li>Conduct research to advance climate AI technology</li>
            <li>Evaluate user satisfaction and response quality</li>
            <li>Debug errors and optimize system architecture</li>
          </ul>

          <h2>6. Data Sharing and Third-Party Processors</h2>
          <p>
            <strong>We do NOT sell, rent, or commercially share your data.</strong> We only share anonymized
            data with trusted processors for specific purposes:
          </p>

          <h3>6.1 Analytics Platform (Langfuse)</h3>
          <ul>
            <li><strong>Purpose:</strong> AI observability and model improvement</li>
            <li><strong>Data Shared:</strong> Anonymized conversation traces (only if you consent)</li>
            <li><strong>Legal Basis:</strong> Your explicit consent (GDPR Article 6(1)(a))</li>
            <li><strong>Safeguards:</strong> Data Processing Agreement, EU-adequate protections</li>
            <li><strong>Your Control:</strong> Opt-out anytime via Privacy Settings</li>
          </ul>

          <h3>6.2 Cloud Infrastructure</h3>
          <ul>
            <li><strong>Purpose:</strong> Secure hosting and service delivery</li>
            <li><strong>Legal Basis:</strong> Contractual necessity</li>
            <li><strong>Safeguards:</strong> Enterprise-grade encryption, EU/EEA or adequate country hosting</li>
          </ul>

          <h3>6.3 Legal Disclosures</h3>
          <p>
            We may disclose data when required by law, court order, or to protect our legal rights,
            in compliance with GDPR Article 6(1)(c) and (f).
          </p>

          <h2>7. Your Rights Under GDPR (Chapter III)</h2>
          <p>
            As a data subject under GDPR, you have comprehensive rights over your personal data.
            We are committed to facilitating the exercise of these rights:
          </p>

          <h3>7.1 Right to Withdraw Consent (Article 7(3))</h3>
          <p><strong>Easy Opt-Out:</strong> Manage your analytics consent anytime:</p>
          <ul>
            <li>Click the <strong>"Privacy"</strong> button in the header</li>
            <li>Open <strong>Privacy Settings</strong> modal</li>
            <li>Toggle <strong>"Analytics & Research"</strong> OFF/ON</li>
            <li>Changes take effect immediately for future interactions</li>
          </ul>
          <p>
            <em>Withdrawing consent does not affect the lawfulness of processing based on consent before withdrawal.</em>
          </p>

          <h3>7.2 Right of Access (Article 15)</h3>
          <p>
            Request confirmation of whether we process your data and obtain a copy of:
          </p>
          <ul>
            <li>What data we hold (if any - note: we use anonymization)</li>
            <li>Processing purposes and legal basis</li>
            <li>Categories of data and recipients</li>
            <li>Retention periods</li>
          </ul>

          <h3>7.3 Right to Rectification (Article 16)</h3>
          <p>Request correction of inaccurate or incomplete personal data.</p>

          <h3>7.4 Right to Erasure / "Right to be Forgotten" (Article 17)</h3>
          <p>
            Request deletion of your data when:
          </p>
          <ul>
            <li>Data is no longer necessary for original purpose</li>
            <li>You withdraw consent and no other legal ground exists</li>
            <li>You object to processing and no overriding legitimate grounds exist</li>
            <li>Data was unlawfully processed</li>
          </ul>
          <p>
            <strong>Note:</strong> Due to complete anonymization, we cannot identify specific user data.
            Withdrawing analytics consent prevents future collection.
          </p>

          <h3>7.5 Right to Restrict Processing (Article 18)</h3>
          <p>Request limitation of processing in certain circumstances.</p>

          <h3>7.6 Right to Data Portability (Article 20)</h3>
          <p>
            Receive your data in structured, machine-readable format and transmit to another controller.
          </p>

          <h3>7.7 Right to Object (Article 21)</h3>
          <p>
            Object to processing based on legitimate interests. For analytics, simply withdraw consent
            via Privacy Settings.
          </p>

          <h3>7.8 Automated Decision-Making Rights (Article 22)</h3>
          <p>
            Our AI provides information but does not make automated decisions with legal or similarly
            significant effects about you.
          </p>

          <h3>7.9 How to Exercise Your Rights</h3>
          <ul>
            <li><strong>Email:</strong> info@bot.neuroclima.eu</li>
            <li><strong>Response Time:</strong> Within 1 month (extensible to 3 months for complex requests)</li>
            <li><strong>Identity Verification:</strong> We may request proof of identity to protect your privacy</li>
          </ul>

          <h2>8. Data Security (GDPR Article 32)</h2>
          <p>
            We implement appropriate technical and organizational measures to ensure data security:
          </p>

          <h3>8.1 Technical Safeguards</h3>
          <ul>
            <li><strong>Encryption:</strong> TLS/SSL encryption for all data transmission</li>
            <li><strong>Anonymization:</strong> Complete anonymization by design - no personal identifiers</li>
            <li><strong>Access Controls:</strong> Role-based access limitations and authentication</li>
            <li><strong>Secure Infrastructure:</strong> Enterprise-grade cloud hosting with security certifications</li>
            <li><strong>Regular Audits:</strong> Periodic security assessments and vulnerability scanning</li>
          </ul>

          <h3>8.2 Organizational Safeguards</h3>
          <ul>
            <li>Staff training on GDPR and data protection principles</li>
            <li>Data processing agreements with all third-party processors</li>
            <li>Incident response procedures for data breaches</li>
            <li>Regular review and updates of security measures</li>
          </ul>

          <h3>8.3 Data Breach Notification</h3>
          <p>
            In the unlikely event of a data breach affecting personal data, we will:
          </p>
          <ul>
            <li>Notify the relevant supervisory authority within 72 hours (GDPR Article 33)</li>
            <li>Inform affected individuals if high risk to their rights (GDPR Article 34)</li>
            <li>Document the breach and our response measures</li>
          </ul>

          <h2>9. Data Retention and Deletion</h2>

          <h3>9.1 Retention Periods</h3>
          <ul>
            <li><strong>Session Data:</strong> Deleted when session ends (browser storage only)</li>
            <li><strong>Analytics Traces:</strong> Retained for model improvement</li>
            <li><strong>Consent Records:</strong> Maintained for compliance demonstration</li>
          </ul>

          <h3>9.2 Automated Deletion</h3>
          <p>
            Anonymized data is subject to automated deletion policies. No data is retained indefinitely.
          </p>

          <h2>10. Cookies and Similar Technologies</h2>
          <p>
            <strong>We do NOT use tracking cookies.</strong> We only use:
          </p>
          <ul>
            <li><strong>Essential Storage:</strong> Browser localStorage for consent preferences and session IDs</li>
            <li><strong>Purpose:</strong> Service functionality only</li>
            <li><strong>No Tracking:</strong> No analytics cookies, advertising cookies, or cross-site tracking</li>
          </ul>

          <h2>11. International Data Transfers (GDPR Chapter V)</h2>
          <p>
            Data processing primarily occurs within the EU/EEA. Any transfers outside the EU/EEA comply
            with GDPR requirements through:
          </p>
          <ul>
            <li><strong>Adequacy Decisions:</strong> Transfers to countries with adequate protection (Article 45)</li>
            <li><strong>Standard Contractual Clauses:</strong> EU-approved SCCs where applicable (Article 46)</li>
            <li><strong>Safeguards:</strong> Additional technical measures (encryption, anonymization)</li>
          </ul>

          <h2>12. Children's Privacy</h2>
          <p>
            Our Service is not directed to children under 16. We do not knowingly collect data from
            children. If you believe a child has provided data, contact us for immediate deletion.
          </p>

          <h2>13. Changes to This Privacy Policy</h2>
          <p>
            We reserve the right to update this Privacy Policy to reflect:
          </p>
          <ul>
            <li>Changes in our data processing practices</li>
            <li>Legal or regulatory requirements</li>
            <li>New features or services</li>
          </ul>
          <p>
            <strong>Material changes will be communicated with at least 30 days advance notice</strong> via:
          </p>
          <ul>
            <li>Prominent notice on our Service</li>
            <li>Updated consent banner if consent requirements change</li>
            <li>Email notification if we have your contact information</li>
          </ul>
          <p>
            <em>Last Updated: January 12, 2026 - Version 2.0</em>
          </p>

          <h2>14. Supervisory Authority and Complaints</h2>
          <p>
            You have the right to lodge a complaint with a supervisory authority, particularly in:
          </p>
          <ul>
            <li>Your EU Member State of habitual residence</li>
            <li>Your place of work</li>
            <li>The place of alleged infringement</li>
          </ul>
          <p>
            <strong>EU Data Protection Authorities:</strong> Find your local DPA at{' '}
            <a href="https://edpb.europa.eu/about-edpb/about-edpb/members_en" target="_blank" rel="noopener noreferrer">
              https://edpb.europa.eu
            </a>
          </p>

          <h2>15. Contact Information</h2>
          <p>
            For questions, concerns, or to exercise your GDPR rights:
          </p>
          <p>
            <strong>Data Controller:</strong> NeuroClimaBot<br/>
            <strong>Email:</strong> info@bot.neuroclima.eu<br/>
            <strong>Privacy Inquiries:</strong> Include "GDPR Request" in subject line
          </p>
          <p>
            We are committed to responding to all inquiries within the GDPR-mandated timeframes.
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
        <p><strong>Last updated:</strong> January 12, 2026</p>
        <p><strong>Effective Date:</strong> January 12, 2026</p>

        <h2>1. General Information Disclaimer</h2>
        <p>
          The NeuroClima Bot service ("Service") provides AI-generated information about
          climate policy and environmental topics for informational and educational purposes only.
          The information provided should not be considered as professional advice, legal counsel,
          or authoritative policy guidance.
        </p>
        <p>
          <strong>Your use of the Service is entirely at your own risk.</strong> We provide the Service
          on an "as is" and "as available" basis without any warranties.
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
          <strong>Email:</strong> info@bot.neuroclima.eu<br/>
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
        <p><strong>Last updated:</strong> January 12, 2026</p>
        <p><strong>Effective Date:</strong> January 12, 2026</p>

        <h2>1. Agreement to Terms</h2>
        <p>
          By accessing or using the NeuroClima Bot service ("Service"), you agree to be bound by
          these Terms of Use ("Terms"). If you do not agree to these Terms, you may not use the Service.
        </p>
        <p>
          These Terms incorporate our Privacy Policy and Disclaimer by reference. By using the Service,
          you also agree to those policies.
        </p>

        <h2>2. Description of Service</h2>
        <p>
          NeuroClima Bot is an AI-powered conversational service that provides information about
          climate policy and environmental topics through advanced machine learning and retrieval
          systems.
        </p>
        <p>
          <strong>Development Phase:</strong> The Service is continuously improving with new features,
          updates, and optimizations. Your feedback helps us enhance accuracy and functionality.
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

        <h3>6.1 Consent Management</h3>
        <ul>
          <li><strong>User Control:</strong> You control analytics data collection via Privacy Settings</li>
          <li><strong>Opt-Out Model:</strong> Analytics enabled by default; opt-out anytime</li>
          <li><strong>Essential Data:</strong> Minimal data required for service functionality (cannot be disabled)</li>
        </ul>

        <h3>6.2 Data Protection Commitments</h3>
        <ul>
          <li><strong>Complete Anonymization:</strong> No personal identifiers in any collected data</li>
          <li><strong>GDPR Compliance:</strong> Full compliance with EU data protection regulations</li>
          <li><strong>Langfuse Analytics:</strong> Optional AI observability for system improvement (with your consent)</li>
          <li><strong>Your Rights:</strong> Access, rectification, erasure, and data portability under GDPR</li>
          <li><strong>No Tracking:</strong> No cookies, no cross-site tracking, no user profiling</li>
        </ul>

        <h3>6.3 Managing Your Privacy</h3>
        <p>
          Access Privacy Settings anytime by clicking the <strong>"Privacy"</strong> button in the header.
          Toggle analytics consent ON/OFF instantly - changes apply immediately.
        </p>

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
          <strong>General Inquiries:</strong> info@bot.neuroclima.eu<br/>
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
          <strong>General Questions:</strong> info@bot.neuroclima.eu<br/>
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