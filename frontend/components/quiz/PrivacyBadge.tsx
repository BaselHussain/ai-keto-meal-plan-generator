'use client';

interface PrivacyBadgeProps {
  /** Optional custom text. Defaults to "100% Private & Confidential" */
  text?: string;
  /** Optional additional CSS classes */
  className?: string;
}

export function PrivacyBadge({
  text = '100% Private & Confidential',
  className = ''
}: PrivacyBadgeProps) {
  return (
    <div className={`flex items-center justify-center space-x-2 p-3 bg-green-50 border border-green-200 rounded-lg ${className}`}>
      <svg
        className="w-5 h-5 text-green-600"
        fill="currentColor"
        viewBox="0 0 20 20"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
          clipRule="evenodd"
        />
      </svg>
      <span className="text-sm font-medium text-green-800">
        {text}
      </span>
    </div>
  );
}
