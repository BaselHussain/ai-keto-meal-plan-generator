import { QuizContainer } from '@/components/quiz';
import Header from '@/components/Header';

export default function QuizPage() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Header />
      <main className="flex-grow">
        <QuizContainer />
      </main>
    </div>
  );
}