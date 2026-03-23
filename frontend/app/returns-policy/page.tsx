import Header from "@/components/Header";
import Footer from "@/components/Footer";

export default function ReturnsPolicyPage() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Header />
      <main className="flex-grow container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Returns Policy</h1>

        <div className="prose prose-gray max-w-none bg-white p-6 rounded-lg shadow-sm">
          <p><strong>Last updated:</strong> February 27, 2026</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Digital Service Policy</h2>
          <p>Since Keto Meal Plan Generator provides digital services (personalized meal plans), our returns policy is limited to specific circumstances.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Refund Eligibility</h2>
          <p>Refunds may be considered in the following situations:</p>
          <ul className="list-disc pl-6 mt-2">
            <li>Technical issues preventing access to your meal plan</li>
            <li>Service not delivered as described</li>
            <li>Billing errors</li>
          </ul>

          <h2 className="text-xl font-semibold mt-6 mb-3">Refund Process</h2>
          <p>To request a refund, please contact our support team within 7 days of purchase. We will review your request and respond within 5-7 business days.</p>

          <h2 className="text-xl font-semibold mt-6 mb-3">Non-Refundable Situations</h2>
          <p>Refunds will not be provided for:</p>
          <ul className="list-disc pl-6 mt-2">
            <li>Change of mind after receiving the service</li>
            <li>Failure to use the meal plan as intended</li>
            <li>Results that differ from personal expectations</li>
          </ul>

          <h2 className="text-xl font-semibold mt-6 mb-3">Contact Information</h2>
          <p>For any questions about our Returns Policy, please contact us at returns@ketomealplangenerator.com</p>
        </div>
      </main>
      <Footer />
    </div>
  );
}