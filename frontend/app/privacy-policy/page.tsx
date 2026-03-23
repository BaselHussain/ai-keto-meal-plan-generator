import Header from "@/components/Header";
import Footer from "@/components/Footer";

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Header />
      <main className="flex-grow container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Privacy Policy</h1>

        <div className="prose prose-gray max-w-none bg-white p-6 rounded-lg shadow-sm">
          <p><strong>Last updated:</strong> February 27, 2026</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Introduction</h2>
          <p>Welcome to Keto Meal Plan Generator's Privacy Policy. Your privacy is important to us, and we are committed to protecting your personal information.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Information We Collect</h2>
          <p>We collect information you provide directly to us, including but not limited to your dietary preferences, health information, and contact details.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">How We Use Your Information</h2>
          <p>We use your information to create personalized keto meal plans, improve our services, and communicate with you about your account.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Data Security</h2>
          <p>We implement appropriate security measures to protect your personal information against unauthorized access, alteration, disclosure, or destruction.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Your Rights</h2>
          <p>You have the right to access, update, or delete your personal information at any time. Contact us if you wish to exercise these rights.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Changes to This Policy</h2>
          <p>We may update this privacy policy from time to time. We will notify you of any changes by posting the new policy on this page.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Contact Us</h2>
          <p>If you have questions about this privacy policy, please contact us at privacy@ketomealplangenerator.com</p>
        </div>
      </main>
      <Footer />
    </div>
  );
}