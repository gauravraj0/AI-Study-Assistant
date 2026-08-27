import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

const NAV = [
  { to: "/", label: "Dashboard", icon: "📊", end: true },
  { to: "/documents", label: "Documents", icon: "📚" },
  { to: "/chat", label: "AI Tutor", icon: "🤖" },
  { to: "/quizzes", label: "Quizzes", icon: "📝" },
  { to: "/flashcards", label: "Flashcards", icon: "🃏" },
  { to: "/plans", label: "Study Plan", icon: "🗓️" },
  { to: "/analytics", label: "Analytics", icon: "📈" },
  { to: "/history", label: "History", icon: "🕘" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">🎓</span>
          <div>
            <div className="brand-name">AI Study Assistant</div>
            <div className="brand-sub">Learn smarter</div>
          </div>
        </div>
        <nav>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}>
              <span className="nav-icon">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="user-chip">
            <div className="avatar">{(user?.name || "?").slice(0, 1).toUpperCase()}</div>
            <div className="user-meta">
              <div className="user-name">{user?.name}</div>
              <div className="user-email">{user?.email}</div>
            </div>
          </div>
          <button
            className="btn ghost small"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
