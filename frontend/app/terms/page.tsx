import Header from "@/components/Header";
import Footer from "@/components/Footer";

export default function TermsPage() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Header />
      <main className="flex-grow container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Terms of Service</h1>

        <div className="prose prose-gray max-w-none bg-white p-6 rounded-lg shadow-sm">
          <p><strong>Last updated:</strong> February 27, 2026</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Acceptance of Terms</h2>
          <p>By accessing and using Keto Meal Plan Generator, you accept and agree to be bound by the terms and provisions of this agreement.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Description of Service</h2>
          <p>We provide personalized keto meal plans based on user-provided information and preferences. The service is designed to assist with dietary planning.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">User Responsibilities</h2>
          <p>You are responsible for maintaining the accuracy of your information and for all activities that occur under your account.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Limitations of Service</h2>
          <p>The meal plans provided are for informational purposes only and should not be considered medical advice. Consult with a healthcare provider before making significant dietary changes.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Intellectual Property</h2>
          <p>All content, features, and functionality of our service are the exclusive property of Keto Meal Plan Generator and are protected by intellectual property laws.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Termination</h2>
          <p>We may terminate or suspend your account immediately, without prior notice, for any reason whatsoever, including without limitation if you breach the terms.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Changes to Terms</h2>
          <p>We reserve the right to modify these terms at any time. Continued use of the service after changes constitutes acceptance of the new terms.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Contact Information</h2>
          <p>If you have questions about these Terms of Service, please contact us at legal@ketomealplangenerator.com</p>
        </div>
      </main>
      <Footer />
    </div>
  );
}