"use client";

import { useState, useEffect } from "react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

interface BlogContent {
  title: string;
  content: string;
  key_takeaways: string[];
  mistakes_to_avoid: string[];
}

export default function BlogPage() {
  const [blogData, setBlogData] = useState<BlogContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchBlogContent = async () => {
      try {
        const response = await fetch("/api/v1/blog/content");
        if (!response.ok) {
          throw new Error("Failed to fetch blog content");
        }
        const data = await response.json();
        setBlogData(data);
      } catch (err) {
        setError("Failed to load blog content. Showing static content instead.");
        // Fallback content in case API fails
        setBlogData({
          title: "Keto Diet Insights & Personalization",
          content: `Starting a weight loss journey can be tough, but with the right help, it's doable and lasting. The Custom Keto Diet Meal Plan gives you a plan made just for you. It fits your needs and likes.

Why Personalization Matters in Keto Dieting
Personalization is crucial for diet success, especially with the keto diet. A custom keto plan considers your nutritional needs and goals. It makes the diet effective and easy to stick to.
Personalizing your keto plan can:
Make sticking to the diet easier
Improve nutritional balance
Help you lose and keep off weight

What Is a Custom Keto Diet Meal Plan
A custom keto diet meal plan is made just for you. It helps you get into ketosis by focusing on what you need and like. This way, you can stick to it and enjoy it.
To make a custom keto diet meal plan, we look at your health, what you like to eat, and your lifestyle. We use this info to create a meal plan that helps you get into ketosis. It also makes sure you get all the nutrients you need and that you're happy with your food choices.

How the Personalization Process Works?
First, we ask you a lot of questions. We want to know about your health goals, food likes, and how you live your life. This helps us figure out the best diet plan for you.
We look at your weight, how active you are, and any food rules you have. Then, we create a meal plan just for you. It's designed to help you do well on the keto diet.

The Difference Between Generic and Custom Keto Plans
Generic keto plans are the same for everyone. They might not work as well for people with special needs or tastes. Custom keto plans, on the other hand, are made just for you. They offer a better way to get into and stay in ketosis.
Choosing a custom keto diet meal plan means you get a diet that really works for you. It's a great way to lose weight and improve your health.`,
          key_takeaways: [
            "A personalized approach to weight loss through a tailored keto plan",
            "Includes a meal plan, food selection report, and shopping list for ease",
            "Simplifies the keto diet process with calorie estimates and food combination guidance",
            "Highlights common keto mistakes to avoid for better results",
            "Designed for individuals seeking a structured weight loss journey",
            "Supports healthy and sustainable weight loss"
          ],
          mistakes_to_avoid: [
            "Not tracking your macros properly - It's important to maintain the right balance of fats, proteins, and carbs to stay in ketosis",
            "Eating too much protein - Excessive protein can kick you out of ketosis as it can be converted to glucose",
            "Not drinking enough water - Dehydration is common when starting keto due to water loss from glycogen depletion",
            "Neglecting electrolytes - Low carb diets can cause electrolyte imbalances leading to keto flu symptoms",
            "Consuming hidden carbs in 'keto-friendly' products - Many processed keto foods contain hidden carbs that add up",
            "Going too low on carbs too quickly - This can cause uncomfortable side effects and make the transition harder",
            "Not eating enough healthy fats - On keto, fats become your primary energy source, so they're crucial",
            "Skipping meals or not eating enough - This can lead to energy crashes and difficulty maintaining the diet",
            "Not planning meals ahead - Lack of planning can lead to poor food choices when you're hungry",
            "Comparing your progress to others - Everyone's journey is different, and individual results vary based on many factors"
          ]
        });
      } finally {
        setLoading(false);
      }
    };

    fetchBlogContent();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading blog content...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Header />
      <main className="flex-grow container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">
          {blogData?.title || "Keto Diet Insights & Personalization"}
        </h1>

        {error && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-yellow-700">{error}</p>
          </div>
        )}

        <div className="prose prose-gray max-w-none bg-white p-6 rounded-lg shadow-sm">
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-green-700 mb-4">Custom Keto Diet Meal Plan</h2>
            <div className="whitespace-pre-line text-gray-700 leading-relaxed">
              {blogData?.content}
            </div>
          </div>

          <div className="mt-10 border-t pt-8">
            <h2 className="text-2xl font-semibold text-green-700 mb-4">Key Takeaways</h2>
            <ul className="list-disc pl-6 space-y-2 text-gray-700">
              {blogData?.key_takeaways.map((takeaway, index) => (
                <li key={index} className="mb-2">
                  <span className="font-medium">{takeaway}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-10 border-t pt-8">
            <h2 className="text-2xl font-semibold text-green-700 mb-4">Mistakes to Avoid in Keto Meal Planning</h2>
            <p className="text-gray-700 mb-4">To ensure success on your keto journey, be mindful of these common mistakes:</p>
            <ul className="list-disc pl-6 space-y-2 text-gray-700">
              {blogData?.mistakes_to_avoid.map((mistake, index) => (
                <li key={index} className="mb-2">
                  <span className="font-medium">{mistake}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}