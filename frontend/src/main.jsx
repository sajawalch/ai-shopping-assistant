import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./App.css";

// Shows the real error on the page instead of a blank screen.
class ErrorBoundary extends React.Component {
  state = { error: null };
  static getDerivedStateFromError(error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <pre style={{ padding: 20, color: "#a1261b", whiteSpace: "pre-wrap" }}>
          The app crashed:{"\n\n"}{String(this.state.error.stack || this.state.error)}
        </pre>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")).render(
  <ErrorBoundary><App /></ErrorBoundary>
);
