const CONTEXT_ENDPOINT = "/api/mobile-shell/context/";

export async function fetchMobileShellContext() {
  const response = await fetch(CONTEXT_ENDPOINT, {
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const error = new Error("Impossibile caricare il contesto mobile");
    error.status = response.status;
    throw error;
  }

  return response.json();
}
