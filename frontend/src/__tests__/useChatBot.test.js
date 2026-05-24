import { act, renderHook, waitFor } from "@testing-library/react";
import { getApiErrorMessage } from "../api/api";
import { sendChatBotMessage } from "../api/chatbot";
import { AuthContext } from "../context/AuthContext";
import { useChatBot } from "../hooks/useChatBot";

jest.mock("../api/chatbot", () => ({
  sendChatBotMessage: jest.fn(),
}));

jest.mock("../api/api", () => ({
  __esModule: true,
  default: {},
  getApiErrorMessage: jest.fn((error, fallback) => {
    const data = error?.response?.data;
    if (data?.detail) return data.detail;
    return fallback;
  }),
}));

function wrapper({ children }) {
  return (
    <AuthContext.Provider value={{ user: { email: "test@test.com" } }}>
      {children}
    </AuthContext.Provider>
  );
}

describe("useChatBot", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getApiErrorMessage.mockImplementation((error, fallback) => {
      const data = error?.response?.data;
      if (data?.detail) return data.detail;
      return fallback;
    });
  });

  it("calls sendChatBotMessage with message and empty history", async () => {
    sendChatBotMessage.mockResolvedValueOnce({ answer: "hi there" });
    const { result } = renderHook(() => useChatBot(), { wrapper });

    await act(async () => {
      await result.current.sendMessage("hello");
    });

    await waitFor(async () => {
      expect(sendChatBotMessage).toHaveBeenCalledWith(
        expect.objectContaining({ message: "hello", history: [] })
      );
    });
  });

  it("appends user and assistant turns when the API returns an answer", async () => {
    sendChatBotMessage.mockResolvedValueOnce({ answer: "hi there" });
    const { result } = renderHook(() => useChatBot(), { wrapper });

    await act(async () => {
      await result.current.sendMessage("hello");
    });

    await waitFor(async () => {
      expect(result.current.turns).toEqual([
        { role: "user", text: "hello" },
        { role: "assistant", text: "hi there" },
      ]);
    });
  });

  it("sets error state from response.data.detail when the API throws", async () => {
    sendChatBotMessage.mockRejectedValueOnce({
      response: { data: { detail: "Server error" } },
    });
    const { result } = renderHook(() => useChatBot(), { wrapper });

    await act(async () => {
      await result.current.sendMessage("hello");
    });

    await waitFor(async () => {
      expect(result.current.error).toBe("Server error");
    });
  });
});
