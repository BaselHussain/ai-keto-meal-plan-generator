import Link from "next/link";
import Header from "@/components/Header";
import FeatureCard from "@/components/FeatureCard";
import Footer from "@/components/Footer";
import { CheckCircle, Clock, Shield, Star, Users } from "lucide-react";

export default function Home() {
  // Example key features data
  const keyFeatures = [
    {
      icon: <CheckCircle className="w-6 h-6" />,
      title: "30-Day Meal Plans",
      description: "Get a complete 30-day keto meal plan with breakfast, lunch, and dinner recipes."
    },
    {
      icon: <Clock className="w-6 h-6" />,
      title: "Time-Saving Recipes",
      description: "Quick and easy recipes that fit into your busy lifestyle without compromising taste."
    },
    {
      icon: <Shield className="w-6 h-6" />,
      title: "Keto Certified",
      description: "All recipes are carefully crafted to meet strict keto guidelines for optimal results."
    },
    {
      icon: <Users className="w-6 h-6" />,
      title: "Personalized Plans",
      description: "Meal plans tailored to your dietary preferences, goals, and restrictions."
    },
    {
      icon: <Star className="w-6 h-6" />,
      title: "Expert Guidance",
      description: "Created by nutrition experts to maximize your success on the keto diet."
    }
  ];

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-gray-50 to-white">
      <Header />
      {/* Hero Section */}
      <div className="relative bg-gradient-to-r from-green-50 to-emerald-50 py-16 md:py-24">
        <div className="container mx-auto px-4 relative z-10">
          <div className="max-w-4xl mx-auto text-center">
            <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
              Transform Your Health with Personalized Keto Meal Plans
            </h1>
            <p className="text-xl text-gray-700 mb-10 max-w-2xl mx-auto">
              Get your custom 30-day keto meal plan designed specifically for your body type, goals, and preferences. Start your journey to better health today.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/quiz"
                className="bg-green-600 hover:bg-green-700 text-white font-bold py-4 px-8 rounded-lg text-lg transition-colors duration-300 shadow-lg"
              >
                Get My Meal Plan
              </Link>
              <Link
                href="#features"
                className="bg-white hover:bg-gray-100 text-green-600 font-bold py-4 px-8 rounded-lg text-lg border-2 border-green-600 transition-colors duration-300"
              >
                Learn More
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div id="features" className="py-16 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Why Choose Our Keto Meal Plans
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Our personalized meal plans take the guesswork out of healthy eating
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {keyFeatures.map((feature, index) => (
              <FeatureCard
                key={index}
                icon={feature.icon}
                title={feature.title}
                description={feature.description}
              />
            ))}
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="py-16 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Getting your personalized meal plan is simple and fast
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center p-6 bg-white rounded-xl shadow-sm">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-green-600">1</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Take Our Quiz</h3>
              <p className="text-gray-600">
                Answer a few questions about your dietary preferences, goals, and restrictions
              </p>
            </div>

            <div className="text-center p-6 bg-white rounded-xl shadow-sm">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-green-600">2</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Get Your Plan</h3>
              <p className="text-gray-600">
                Our system generates your personalized 30-day keto meal plan
              </p>
            </div>

            <div className="text-center p-6 bg-white rounded-xl shadow-sm">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-green-600">3</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Start Eating</h3>
              <p className="text-gray-600">
                Download your meal plan and start cooking with easy, delicious recipes
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-16 bg-gradient-to-r from-green-500 to-emerald-600 text-white">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Ready to Transform Your Health?
          </h2>
          <p className="text-xl mb-8 max-w-2xl mx-auto text-green-100">
            Join thousands of people who have successfully reached their health goals with our personalized keto meal plans.
          </p>
          <Link
            href="/quiz"
            className="inline-block bg-white text-green-600 hover:bg-gray-100 font-bold py-4 px-8 rounded-lg text-lg transition-colors duration-300 shadow-lg"
          >
            Get Started Now
          </Link>
        </div>
      </div>

      <Footer />
    </div>
  );
}