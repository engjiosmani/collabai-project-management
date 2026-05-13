import { render, screen } from "@testing-library/react";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";

jest.mock(
  "react-router-dom",
  () => ({
    Routes: ({ children }) => <>{children}</>,
    Route: ({ element }) => <>{element}</>,
    Navigate: () => null,
    Link: ({ children, to }) => <a href={to}>{children}</a>,
    useNavigate: () => jest.fn(),
  }),
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
