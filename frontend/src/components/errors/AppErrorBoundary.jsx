import { Component } from "react";

import ErrorFallback from "../ui/ErrorFallback";

class AppErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = { error: null };
    }

    static getDerivedStateFromError(error) {
        return { error };
    }

    componentDidCatch(error, errorInfo) {
        if (process.env.NODE_ENV !== "production") {
            console.error("Unhandled React error", error, errorInfo);
        }
    }

    handleReload = () => {
        window.location.reload();
    };

    render() {
        if (this.state.error) {
            return (
                <ErrorFallback
                    error={this.state.error}
                    onReload={this.handleReload}
                    description="The interface hit an unexpected problem. Reloading will start a clean session."
                />
            );
        }

        return this.props.children;
    }
}

export default AppErrorBoundary;
