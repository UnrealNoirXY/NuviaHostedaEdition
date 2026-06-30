import axios from "axios";

// Helper function to get a cookie by name
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const resolveApiBaseUrl = () => {
  if (typeof window === "undefined") {
    return "/";
  }

  const metaBase = document.querySelector('meta[name="api-base-url"]')?.getAttribute("content");
  if (metaBase) {
    return metaBase;
  }

  return window.location.origin;
};

// Create a centralized Axios instance
const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(), // Default to same-origin, allow override via meta tag
  withCredentials: true, // Send cookies with requests
  headers: {
    "X-Requested-With": "XMLHttpRequest",
    Accept: "application/json",
  },
});

// Add a request interceptor to automatically attach the CSRF token
apiClient.interceptors.request.use((config) => {
  const method = (config.method || "get").toLowerCase();
  // Attach CSRF token only to "unsafe" methods (POST, PUT, DELETE, etc.)
  const unsafeMethods = ["post", "put", "delete", "patch"];

  if (unsafeMethods.includes(method)) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) {
      config.headers["X-CSRFToken"] = csrfToken;
    }
  }

  return config;
});

export default apiClient;
