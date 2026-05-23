import { render, screen } from "@testing-library/react";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";

jest.mock(
  "react-router-dom",
  () => {
    const React = require("react");

    return {
      Routes: ({ children }) => {
        const loginRoute = React.Children.toArray(children).find(
          (child) => child.props.path === "/login"
        );
        return loginRoute?.props.element ?? null;
      },
      Route: () => null,
      Navigate: () => null,
      Link: ({ children, to }) => <a href={to}>{children}</a>,
      useNavigate: () => jest.fn(),
      useLocation: () => ({ state: null }),
    };
  },
  { virtual: true }
);

test("renders the login screen at the login route", () => {
  render(
    <AuthProvider>
      <App />
    </AuthProvider>
  );

  expect(screen.getByText(/welcome back/i)).toBeInTheDocument();
});
