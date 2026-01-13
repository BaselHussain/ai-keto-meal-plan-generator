import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Privacy Policy | AI Keto Meal Plan Generator',
  description: 'Privacy policy and data handling practices for the AI-powered Keto Meal Plan Generator.',
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-md p-8 md:p-12">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/"
            className="inline-flex items-center text-green-600 hover:text-green-700 mb-4 text-sm font-medium"
          >
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Back to Home
          </Link>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">
            Privacy Policy
          </h1>
          <p className="text-gray-600">
            Last Updated: January 2026
          </p>
        </div>

        {/* Privacy Badge */}
        <div className="mb-8 p-4 bg-green-50 border-2 border-green-200 rounded-lg">
          <div className="flex items-center space-x-3">
            <svg
              className="w-8 h-8 text-green-600 flex-shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                clipRule="evenodd"
              />
            </svg>
            <div>
              <h2 className="text-lg font-bold text-green-900">
                Your Privacy is Our Priority
              </h2>
              <p className="text-sm text-green-800">
                We are committed to protecting your personal information and being transparent about our data practices.
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="prose prose-gray max-w-none space-y-8">
          {/* Section 1: Introduction */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">1. Introduction</h2>
            <p className="text-gray-700 mb-4">
              This Privacy Policy explains how we collect, use, store, and delete your personal information
              when you use our AI-powered Keto Meal Plan Generator service (&quot;Service&quot;). By using our Service,
              you agree to the practices described in this policy.
            </p>
            <p className="text-gray-700">
              We are committed to GDPR compliance and protecting your privacy rights under applicable data
              protection laws.
            </p>
          </section>

          {/* Section 2: Information We Collect */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">2. Information We Collect</h2>
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">2.1 Quiz Responses</h3>
                <p className="text-gray-700 mb-2">When you complete our 20-step quiz, we collect:</p>
                <ul className="list-disc list-inside text-gray-700 space-y-1 ml-4">
                  <li>Gender</li>
                  <li>Activity level</li>
                  <li>Food preferences (proteins, vegetables, fats, dairy, etc.)</li>
                  <li>Dietary restrictions and allergies</li>
                  <li>Biometric data: age, weight, height</li>
                  <li>Health goal (weight loss, maintenance, or muscle gain)</li>
                </ul>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">2.2 Payment Information</h3>
                <p className="text-gray-700">
                  We use Paddle as our payment processor. Your payment card details are handled directly by Paddle
                  and are never stored on our servers. We only receive transaction metadata (payment ID, email,
                  transaction status) necessary to fulfill your order.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">2.3 Email Address</h3>
                <p className="text-gray-700">
                  We collect your email address to:
                </p>
                <ul className="list-disc list-inside text-gray-700 space-y-1 ml-4">
                  <li>Verify your identity before payment</li>
                  <li>Deliver your personalized meal plan PDF</li>
                  <li>Enable account recovery via magic links</li>
                  <li>Provide customer support (if requested)</li>
                </ul>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">2.4 Technical Data</h3>
                <p className="text-gray-700">
                  We automatically collect limited technical information including IP addresses and browser type
                  for security purposes (fraud prevention, rate limiting) and service improvement.
                </p>
              </div>
            </div>
          </section>

          {/* Section 3: How We Use Your Information */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">3. How We Use Your Information</h2>
            <p className="text-gray-700 mb-4">
              Your personal information is used exclusively for the following purposes:
            </p>
            <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
              <li>
                <strong>Calorie Calculation:</strong> Using the Mifflin-St Jeor formula to determine your personalized
                daily calorie target based on your biometric data, activity level, and health goal
              </li>
              <li>
                <strong>AI Meal Plan Generation:</strong> Creating a 30-day ketogenic meal plan tailored to your
                food preferences, dietary restrictions, and calorie target
              </li>
              <li>
                <strong>PDF Delivery:</strong> Generating and delivering your personalized meal plan as a PDF
                document via email
              </li>
              <li>
                <strong>Account Recovery:</strong> Enabling you to re-download your meal plan within the 90-day
                retention period via magic link or account login
              </li>
              <li>
                <strong>Fraud Prevention:</strong> Detecting and preventing duplicate purchases, chargebacks,
                and refund abuse
              </li>
              <li>
                <strong>Service Improvement:</strong> Analyzing aggregate, anonymized data to improve our AI
                meal plan quality and user experience
              </li>
            </ul>
            <p className="text-gray-700 mt-4">
              <strong>We never:</strong> Sell your data, share it with third parties for marketing purposes,
              or use it for purposes other than those stated above.
            </p>
          </section>

          {/* Section 4: Data Retention */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">4. Data Retention & Automatic Deletion</h2>
            <p className="text-gray-700 mb-4">
              We implement strict data retention policies to minimize how long we store your personal information:
            </p>

            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-4">
              <h3 className="text-lg font-semibold text-blue-900 mb-2">Automatic Deletion Schedule</h3>
              <ul className="list-disc list-inside text-blue-900 space-y-2 ml-4">
                <li>
                  <strong>Biometric Data (age, weight, height):</strong> Deleted 24 hours after PDF delivery
                </li>
                <li>
                  <strong>Quiz Responses (food preferences, restrictions):</strong> Deleted 24 hours after PDF delivery
                  for paid customers; 7 days after submission for unpaid/incomplete orders
                </li>
                <li>
                  <strong>Meal Plan Metadata:</strong> Retained for 90 days to enable re-downloads, then automatically deleted
                </li>
                <li>
                  <strong>PDF Files:</strong> Deleted 91 days after creation (90-day retention + 24-hour grace period)
                </li>
                <li>
                  <strong>Magic Link Tokens:</strong> Expired and deleted after 24 hours or after single use
                </li>
                <li>
                  <strong>Email Blacklist (chargebacks/refund abuse):</strong> Deleted after 90 days
                </li>
              </ul>
            </div>

            <p className="text-gray-700">
              All deletions are logged for compliance audit purposes and are performed automatically by scheduled
              cleanup jobs.
            </p>
          </section>

          {/* Section 5: Data Security */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">5. Data Security</h2>
            <p className="text-gray-700 mb-4">
              We implement industry-standard security measures to protect your data:
            </p>
            <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
              <li>
                <strong>Encryption:</strong> All data is transmitted over HTTPS (TLS 1.3) and encrypted at rest
              </li>
              <li>
                <strong>PCI Compliance:</strong> Payment processing through Paddle, a PCI DSS Level 1 certified provider
              </li>
              <li>
                <strong>Access Controls:</strong> Strict access controls with API key authentication and IP whitelisting
                for administrative functions
              </li>
              <li>
                <strong>Secure Storage:</strong> Database hosted on Neon (serverless PostgreSQL) with automatic backups
              </li>
              <li>
                <strong>Error Monitoring:</strong> Real-time security monitoring via Sentry for anomaly detection
              </li>
              <li>
                <strong>Rate Limiting:</strong> Protection against brute force attacks and abuse via Redis-backed rate limiting
              </li>
            </ul>
          </section>

          {/* Section 6: Third-Party Services */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">6. Third-Party Services</h2>
            <p className="text-gray-700 mb-4">
              We use the following trusted third-party services to deliver our Service:
            </p>
            <div className="space-y-3">
              <div className="p-3 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-800">Paddle (Payment Processing)</h3>
                <p className="text-sm text-gray-700">
                  PCI DSS Level 1 certified payment processor. Handles all payment card data.
                </p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-800">OpenAI (AI Meal Plan Generation)</h3>
                <p className="text-sm text-gray-700">
                  Processes your food preferences and calorie target to generate personalized meal plans.
                  Data is not used for model training.
                </p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-800">Resend (Email Delivery)</h3>
                <p className="text-sm text-gray-700">
                  Transactional email service for delivering your PDF and recovery links.
                </p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-800">Vercel Blob (PDF Storage)</h3>
                <p className="text-sm text-gray-700">
                  Secure cloud storage for your meal plan PDF with time-limited signed URLs.
                </p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-800">Neon (Database)</h3>
                <p className="text-sm text-gray-700">
                  Serverless PostgreSQL database for storing quiz responses and meal plan metadata.
                </p>
              </div>
            </div>
            <p className="text-gray-700 mt-4">
              Each third-party service is carefully vetted for security and GDPR compliance.
            </p>
          </section>

          {/* Section 7: Your Rights (GDPR) */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">7. Your Privacy Rights (GDPR)</h2>
            <p className="text-gray-700 mb-4">
              Under GDPR and applicable data protection laws, you have the following rights:
            </p>
            <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
              <li>
                <strong>Right to Access:</strong> Request a copy of your personal data we hold
              </li>
              <li>
                <strong>Right to Rectification:</strong> Request correction of inaccurate data
              </li>
              <li>
                <strong>Right to Erasure (&quot;Right to be Forgotten&quot;):</strong> Request deletion of your
                personal data before the automatic deletion schedule
              </li>
              <li>
                <strong>Right to Restrict Processing:</strong> Request limitation on how we use your data
              </li>
              <li>
                <strong>Right to Data Portability:</strong> Receive your data in a structured, machine-readable format
              </li>
              <li>
                <strong>Right to Object:</strong> Object to processing of your personal data
              </li>
              <li>
                <strong>Right to Withdraw Consent:</strong> Withdraw consent at any time (does not affect prior processing)
              </li>
            </ul>
            <p className="text-gray-700 mt-4">
              To exercise any of these rights, please contact us at{' '}
              <a href="mailto:privacy@ketomealplan.ai" className="text-green-600 hover:text-green-700 font-medium">
                privacy@ketomealplan.ai
              </a>
              . We will respond within 30 days.
            </p>
          </section>

          {/* Section 8: Cookies */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">8. Cookies & Local Storage</h2>
            <p className="text-gray-700 mb-4">
              We use minimal cookies and browser local storage:
            </p>
            <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
              <li>
                <strong>Essential Cookies:</strong> Session management and authentication (required for service functionality)
              </li>
              <li>
                <strong>Local Storage:</strong> Saving your quiz progress so you can continue later
                (stored only on your device, not sent to our servers until you complete the quiz)
              </li>
            </ul>
            <p className="text-gray-700 mt-4">
              We do not use tracking cookies or third-party advertising cookies.
            </p>
          </section>

          {/* Section 9: Children's Privacy */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">9. Children&apos;s Privacy</h2>
            <p className="text-gray-700">
              Our Service is not intended for individuals under 18 years of age. We do not knowingly collect
              personal information from children. If you believe we have inadvertently collected data from a
              minor, please contact us immediately so we can delete it.
            </p>
          </section>

          {/* Section 10: Changes to This Policy */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">10. Changes to This Policy</h2>
            <p className="text-gray-700">
              We may update this Privacy Policy from time to time to reflect changes in our practices or legal
              requirements. We will notify you of material changes by updating the &quot;Last Updated&quot; date at
              the top of this page. Your continued use of the Service after changes constitutes acceptance of
              the updated policy.
            </p>
          </section>

          {/* Section 11: Contact Us */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">11. Contact Us</h2>
            <p className="text-gray-700 mb-4">
              If you have questions about this Privacy Policy or how we handle your data, please contact us:
            </p>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-gray-700">
                <strong>Email:</strong>{' '}
                <a href="mailto:privacy@ketomealplan.ai" className="text-green-600 hover:text-green-700 font-medium">
                  privacy@ketomealplan.ai
                </a>
              </p>
              <p className="text-gray-700 mt-2">
                <strong>Data Protection Officer:</strong>{' '}
                <a href="mailto:dpo@ketomealplan.ai" className="text-green-600 hover:text-green-700 font-medium">
                  dpo@ketomealplan.ai
                </a>
              </p>
            </div>
          </section>

          {/* Section 12: Complaints */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">12. Filing a Complaint</h2>
            <p className="text-gray-700">
              If you believe we have not handled your personal data in accordance with GDPR or applicable data
              protection laws, you have the right to lodge a complaint with your local data protection authority.
            </p>
          </section>
        </div>

        {/* Footer */}
        <div className="mt-12 pt-8 border-t border-gray-200">
          <p className="text-sm text-gray-600 text-center">
            This privacy policy is effective as of January 2026 and applies to all users of the AI Keto Meal Plan Generator.
          </p>
        </div>
      </div>
    </div>
  );
}
