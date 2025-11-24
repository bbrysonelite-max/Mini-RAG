import { type FC } from 'react';

const Footer: FC = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="app-footer">
      <div className="footer-content">
        <div className="footer-section">
          <h4 className="footer-heading">Second Brain RAG System</h4>
          <p className="footer-tagline">
            Powered by AI. Built by{' '}
            <a 
              href="https://alienprobeports.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="footer-link-brand"
            >
              Alien Probe Reports
            </a>
          </p>
        </div>

        <div className="footer-section">
          <h4 className="footer-heading">Product</h4>
          <ul className="footer-links">
            <li><a href="/features" className="footer-link">Features</a></li>
            <li><a href="/pricing" className="footer-link">Pricing</a></li>
            <li><a href="/docs" className="footer-link">Documentation</a></li>
            <li><a href="/api" className="footer-link">API</a></li>
          </ul>
        </div>

        <div className="footer-section">
          <h4 className="footer-heading">Company</h4>
          <ul className="footer-links">
            <li><a href="/about" className="footer-link">About Us</a></li>
            <li><a href="/blog" className="footer-link">Blog</a></li>
            <li><a href="/careers" className="footer-link">Careers</a></li>
            <li>
              <a 
                href="mailto:contact@alienprobeports.com" 
                className="footer-link"
              >
                Contact
              </a>
            </li>
          </ul>
        </div>

        <div className="footer-section">
          <h4 className="footer-heading">Legal</h4>
          <ul className="footer-links">
            <li>
              <a 
                href="/legal/privacy" 
                className="footer-link"
                target="_blank"
                rel="noopener noreferrer"
              >
                Privacy Policy
              </a>
            </li>
            <li>
              <a 
                href="/legal/terms" 
                className="footer-link"
                target="_blank"
                rel="noopener noreferrer"
              >
                Terms of Service
              </a>
            </li>
            <li>
              <a 
                href="/legal/cookies" 
                className="footer-link"
                target="_blank"
                rel="noopener noreferrer"
              >
                Cookie Policy
              </a>
            </li>
            <li>
              <a 
                href="/security" 
                className="footer-link"
                target="_blank"
                rel="noopener noreferrer"
              >
                Security
              </a>
            </li>
          </ul>
        </div>

        <div className="footer-section">
          <h4 className="footer-heading">Support</h4>
          <ul className="footer-links">
            <li>
              <a 
                href="/help" 
                className="footer-link"
              >
                Help Center
              </a>
            </li>
            <li>
              <a 
                href="/faq" 
                className="footer-link"
              >
                FAQ
              </a>
            </li>
            <li>
              <a 
                href="https://status.alienprobeports.com" 
                className="footer-link"
                target="_blank"
                rel="noopener noreferrer"
              >
                System Status
              </a>
            </li>
            <li>
              <a 
                href="mailto:support@alienprobeports.com" 
                className="footer-link"
              >
                Email Support
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom">
        <p className="footer-copyright">
          © {currentYear} <strong>Alien Probe Reports</strong>. All rights reserved.
        </p>
        <div className="footer-social">
          <a 
            href="https://twitter.com/alienprobeports" 
            className="footer-social-link"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Twitter"
          >
            𝕏
          </a>
          <a 
            href="https://linkedin.com/company/alienprobeports" 
            className="footer-social-link"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="LinkedIn"
          >
            in
          </a>
          <a 
            href="https://github.com/alienprobeports" 
            className="footer-social-link"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub"
          >
            GH
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;

