import { Component, type ErrorInfo, type ReactNode } from "react";
import { ErrorState } from "./ui/ErrorState";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}
interface State {
  error: Error | null;
}

/** Capture les erreurs de RENDU (pas les erreurs fetch — celles-ci passent par ErrorState). */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary — erreur de rendu capturée:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        this.props.fallback ?? (
          <ErrorState error={this.state.error} onRetry={() => this.setState({ error: null })} />
        )
      );
    }
    return this.props.children;
  }
}
