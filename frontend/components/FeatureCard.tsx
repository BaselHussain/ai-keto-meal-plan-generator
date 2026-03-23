import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ReactNode } from "react";

interface FeatureCardProps {
  icon: ReactNode;
  title: string;
  description: string;
}

export default function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <Card className="h-full flex flex-col border-0 shadow-none bg-transparent">
      <CardHeader className="p-0 flex flex-row items-start gap-4">
        <div className="mt-1 text-green-600">
          {icon}
        </div>
        <div>
          <CardTitle className="text-lg font-semibold text-gray-900">
            {title}
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="p-0 pt-2">
        <p className="text-gray-600">
          {description}
        </p>
      </CardContent>
    </Card>
  );
}