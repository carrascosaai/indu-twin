const TOKEN_KEY = "indu_twin_token";

export const getStoredToken = (): string | null => localStorage.getItem(TOKEN_KEY);

export const setStoredToken = (token: string): void => localStorage.setItem(TOKEN_KEY, token);

export const clearStoredToken = (): void => localStorage.removeItem(TOKEN_KEY);
