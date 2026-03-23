import Link from "next/link";
import { ReactNode } from "react";

export default function Footer() {
  return (
    <footer className="bg-gray-50 border-t border-gray-200 py-8">
      <div className="container mx-auto px-4">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="mb-4 md:mb-0">
            <p className="text-gray-600 text-sm">
              © {new Date().getFullYear()} Keto Meal Plan Generator. All rights reserved.
            </p>
          </div>

          <div className="flex flex-wrap justify-center gap-6">
            <Link
              href="/privacy-policy"
              className="text-gray-600 hover:text-green-600 transition-colors text-sm"
            >
              Privacy Policy
            </Link>
            <Link
              href="/terms"
              className="text-gray-600 hover:text-green-600 transition-colors text-sm"
            >
              Terms of Service
            </Link>
            <Link
              href="/returns-policy"
              className="text-gray-600 hover:text-green-600 transition-colors text-sm"
            >
              Returns Policy
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}