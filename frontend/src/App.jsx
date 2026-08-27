import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import { Spinner } from "./components/ui.jsx";
import Analytics from "./pages/Analytics.jsx";
import Chat from "./pages/Chat.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import DocumentDetail from "./pages/DocumentDetail.jsx";
import Documents from "./pages/Documents.jsx";
import FlashcardSet from "./pages/FlashcardSet.jsx";
import Flashcards from "./pages/Flashcards.jsx";
import History from "./pages/History.jsx";
import Login from "./pages/Login.jsx";
import Plans from "./pages/Plans.jsx";
import QuizReview from "./pages/QuizReview.jsx";
import QuizTake from "./pages/QuizTake.jsx";
import Quizzes from "./pages/Quizzes.jsx";

function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="page-center">
        <Spinner label="Loading your workspace…" />
      </div>
    );
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="documents" element={<Documents />} />
            <Route path="documents/:id" element={<DocumentDetail />} />
            <Route path="chat" element={<Chat />} />
            <Route path="quizzes" element={<Quizzes />} />
            <Route path="quizzes/take/:id" element={<QuizTake />} />
            <Route path="quizzes/:id" element={<QuizReview />} />
            <Route path="flashcards" element={<Flashcards />} />
            <Route path="flashcards/:id" element={<FlashcardSet />} />
            <Route path="plans" element={<Plans />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="history" element={<History />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
