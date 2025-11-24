import { useState, type FC } from 'react';

interface HelpWidgetProps {
  position?: 'bottom-right' | 'bottom-left';
}

const HelpWidget: FC<HelpWidgetProps> = ({ position = 'bottom-right' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'faq' | 'contact'>('faq');

  const faqs = [
    {
      question: 'How do I upload documents?',
      answer: 'Navigate to the "Ingest" tab, then drag and drop files or paste URLs. Supported formats include PDF, DOCX, TXT, images, and more.'
    },
    {
      question: 'What file types are supported?',
      answer: 'We support PDF, DOCX, TXT, Markdown, VTT/SRT transcripts, and images (PNG, JPG) with OCR. You can also ingest content from URLs.'
    },
    {
      question: 'How do I ask questions?',
      answer: 'Go to the "Ask" tab, type your question in natural language, and click "Ask". The AI will search your documents and generate an answer with sources.'
    },
    {
      question: 'Is my data private?',
      answer: 'Yes! Your documents are private and encrypted. We never use your content to train AI models or share it with others.'
    },
    {
      question: 'Can I delete my documents?',
      answer: 'Yes. Navigate to the "Sources" tab, find the document, and click the delete button. Deletion is permanent.'
    },
    {
      question: 'How accurate are the answers?',
      answer: 'Answers are generated from your documents using GPT-4 or Claude. Always review AI-generated content for critical use cases.'
    }
  ];

  return (
    <>
      {/* Help Button */}
      <button
        className={`help-widget-button ${position}`}
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Help"
        aria-expanded={isOpen}
      >
        {isOpen ? '✕' : '?'}
      </button>

      {/* Help Panel */}
      {isOpen && (
        <div className={`help-widget-panel ${position}`}>
          <div className="help-widget-header">
            <h3 className="help-widget-title">Help Center</h3>
            <button 
              className="help-widget-close"
              onClick={() => setIsOpen(false)}
              aria-label="Close help"
            >
              ✕
            </button>
          </div>

          <div className="help-widget-tabs">
            <button
              className={`help-widget-tab ${activeTab === 'faq' ? 'active' : ''}`}
              onClick={() => setActiveTab('faq')}
            >
              FAQ
            </button>
            <button
              className={`help-widget-tab ${activeTab === 'contact' ? 'active' : ''}`}
              onClick={() => setActiveTab('contact')}
            >
              Contact
            </button>
          </div>

          <div className="help-widget-content">
            {activeTab === 'faq' && (
              <div className="help-faq">
                {faqs.map((faq, index) => (
                  <details key={index} className="help-faq-item">
                    <summary className="help-faq-question">
                      {faq.question}
                    </summary>
                    <p className="help-faq-answer">
                      {faq.answer}
                    </p>
                  </details>
                ))}
                <div className="help-faq-footer">
                  <a 
                    href="/faq" 
                    className="help-link"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View all FAQs →
                  </a>
                </div>
              </div>
            )}

            {activeTab === 'contact' && (
              <div className="help-contact">
                <div className="help-contact-option">
                  <h4 className="help-contact-title">Email Support</h4>
                  <p className="help-contact-desc">
                    Get help via email. We typically respond within 24 hours.
                  </p>
                  <a 
                    href="mailto:support@alienprobeports.com"
                    className="help-contact-button"
                  >
                    Send Email
                  </a>
                </div>

                <div className="help-contact-option">
                  <h4 className="help-contact-title">Documentation</h4>
                  <p className="help-contact-desc">
                    Browse our comprehensive guides and tutorials.
                  </p>
                  <a 
                    href="/docs"
                    className="help-contact-button"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View Docs
                  </a>
                </div>

                <div className="help-contact-option">
                  <h4 className="help-contact-title">System Status</h4>
                  <p className="help-contact-desc">
                    Check if there are any ongoing issues.
                  </p>
                  <a 
                    href="https://status.alienprobeports.com"
                    className="help-contact-button"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View Status
                  </a>
                </div>

                <div className="help-contact-footer">
                  <p className="help-contact-emergency">
                    For urgent security issues:{' '}
                    <a href="mailto:security@alienprobeports.com">
                      security@alienprobeports.com
                    </a>
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="help-widget-footer">
            <p className="help-widget-branding">
              Powered by <strong>Alien Probe Reports</strong>
            </p>
          </div>
        </div>
      )}
    </>
  );
};

export default HelpWidget;

