export const getBackendUrl = (path: string = "") => {
  // Default to 127.0.0.1:8000 to bypass Windows IPv6 localhost resolution conflicts
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  return `${baseUrl}/api${path}`;
};

export const getAuthHeaders = (): Record<string, string> => {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("token");
  return token ? { "Authorization": `Bearer ${token}` } : {};
};

export const getAuthUser = () => {
  if (typeof window === "undefined") return null;
  const userStr = localStorage.getItem("user");
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
};

export const logoutUser = () => {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
};

/**
 * Attempts to use the stored refresh_token to get a fresh access_token.
 * Returns true on success, false if the refresh token is missing or expired.
 */
const tryRefreshToken = async (): Promise<boolean> => {
  if (typeof window === "undefined") return false;
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return false;

  try {
    const res = await fetch(getBackendUrl("/auth/refresh"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      logoutUser();
      return false;
    }
    const data = await res.json();
    if (data.access_token) {
      localStorage.setItem("token", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("refresh_token", data.refresh_token);
      }
      return true;
    }
    return false;
  } catch {
    return false;
  }
};

/**
 * Drop-in replacement for fetch() that automatically refreshes the JWT
 * on a 401 response and retries once. Falls through normally on all other errors.
 */
export const apiFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  // Merge auth headers
  const headers = { ...getAuthHeaders(), ...(options.headers as Record<string, string> || {}) };
  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      // Retry with new token
      const retryHeaders = { ...getAuthHeaders(), ...(options.headers as Record<string, string> || {}) };
      return fetch(url, { ...options, headers: retryHeaders });
    }
    // Refresh failed – redirect to login
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }
  return res;
};

