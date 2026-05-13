import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) return <div className="error-box"><h2>Erro na interface</h2><p>{this.state.error?.message || 'Falha inesperada.'}</p></div>;
    return this.props.children;
  }
}
