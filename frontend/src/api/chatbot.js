import API from "./api";

export async function sendChatBotMessage({ message, history = [], signal = null }) {
  const config = {
    timeout: 120000,
    ...(signal ? { signal } : {}),
  };
  const { data } = await API.post(
    "/ai/chatbot/",
    { message, history },
    config
  );
  return data;
}
