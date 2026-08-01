import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import SentinelTwinXDashboard from './SentinelTwinXDashboard';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(_: Error): State {
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught React error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return <SentinelTwinXDashboard />;
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <SentinelTwinXDashboard />
    </ErrorBoundary>
  );
}
