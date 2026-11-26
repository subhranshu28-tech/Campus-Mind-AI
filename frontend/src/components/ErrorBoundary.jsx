import { Component } from "react";

export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Keep the console report for local debugging and error monitoring hooks.
    console.error("CampusMind UI error", error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="app-shell grid min-h-screen place-items-center p-6 text-slate-900">
        <section className="panel max-w-lg text-center">
          <p className="text-sm font-medium text-blue-700">CampusMind AI</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">Something went wrong</h1>
          <p className="mt-2 text-sm text-slate-500">
            The workspace hit an unexpected error. Your session is still safe; reload to continue.
          </p>
          {this.state.error?.message && (
            <pre className="mt-4 overflow-auto rounded-lg bg-slate-100 p-3 text-left text-xs text-slate-600">
              {this.state.error.message}
            </pre>
          )}
          <button
            onClick={() => window.location.reload()}
            className="mt-5 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Reload workspace
          </button>
        </section>
      </main>
    );
  }
}
