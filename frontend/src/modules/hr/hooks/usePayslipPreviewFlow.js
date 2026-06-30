import { useEffect } from "react";
import apiClient from "../../../apiClient";

const buildCapabilitiesState = (capabilities = {}) => ({
  mode: capabilities?.mode || "async",
  streamAvailable: capabilities?.stream_available !== false,
  pollingAvailable: capabilities?.polling_available !== false,
  ocrEnabled: Boolean(capabilities?.ocr_enabled),
  ocrAvailable: capabilities?.ocr_available,
  renderingAvailable: Boolean(capabilities?.rendering_available),
});


const enrichSegmentsWithPreviewPages = (segments = [], scanPages = []) => {
  const pageMap = new Map();
  scanPages.forEach((page) => {
    if (page && Number.isInteger(page.page_index)) {
      pageMap.set(page.page_index, page);
    }
  });

  return (segments || []).map((segment) => {
    if (!segment || typeof segment !== "object") return segment;
    const hasPreviewPages = Array.isArray(segment.preview_pages);
    const previewPages = hasPreviewPages
      ? segment.preview_pages
      : (() => {
          const pages = [];
          const start = segment.page_start;
          const end = segment.page_end;
          if (Number.isInteger(start) && Number.isInteger(end) && start <= end) {
            for (let idx = start; idx <= end; idx += 1) {
              const page = pageMap.get(idx);
              if (page) pages.push(page);
            }
          }
          return pages;
        })();

    const previewAvailable = typeof segment.preview_available === "boolean"
      ? segment.preview_available
      : previewPages.length > 0;

    return {
      ...segment,
      preview_pages: previewPages,
      preview_available: previewAvailable,
      preview_error_code:
        segment.preview_error_code || (!previewAvailable && !segment.error ? "segment_preview_unavailable" : undefined),
    };
  });
};

const classifyPreviewError = (error) => {
  const statusCode = error?.response?.status;
  const payload = error?.response?.data || {};
  const backendCode = payload?.error_code;
  if (backendCode) {
    return { code: backendCode, message: payload?.detail || "Errore preview." };
  }
  if (statusCode === 401 || statusCode === 403) {
    return {
      code: "auth_error",
      message: "Sessione non valida per la preview. Effettua di nuovo l'accesso.",
    };
  }
  if (statusCode === 400) {
    return {
      code: "invalid_request",
      message: payload?.detail || "Parametri preview non validi.",
    };
  }
  if (error?.name === "AbortError") {
    return { code: "request_aborted", message: "Preview annullata." };
  }
  return {
    code: "preview_unavailable",
    message: payload?.detail || "Impossibile generare l'anteprima.",
  };
};

export default function usePayslipPreviewFlow({
  sourceFile,
  autoMatchStrategy,
  manifestHint,
  ocrEnabled,
  ocrLanguages,
  previewLocked,
  setBatchPreview,
  handlePreviewSegments,
}) {
  useEffect(() => {
    const file = sourceFile;
    if (!file) {
      setBatchPreview({ loading: false, segments: [], error: "", errorCode: "", liveMode: "idle" });
      return;
    }
    if (previewLocked) {
      return;
    }

    let isActive = true;
    let eventSource;
    let pollingTimer;
    const controller = new AbortController();

    const startPolling = (token) => {
      if (!token || !isActive || pollingTimer) return;
      const poll = async () => {
        if (!isActive) return;
        try {
          const res = await apiClient.get(`/api/hr/payslip-batches/preview-status/${token}/`, {
            signal: controller.signal,
          });
          if (!isActive) return;
          const data = res.data || {};
          const previewPayload = data.preview || {};
          const nextSegments = enrichSegmentsWithPreviewPages(previewPayload.segments ?? [], previewPayload.scan_pages ?? []);
          const capabilitiesState = buildCapabilitiesState(data.capabilities || previewPayload.capabilities || {});
          setBatchPreview((prev) => ({
            ...prev,
            ...previewPayload,
            loading: data.status === "running" || data.status === "queued",
            progress: data.progress_percent ?? prev.progress ?? 0,
            error:
              data.status === "failed"
                ? data.error_message || prev.error || "Preview fallita."
                : prev.error || "Connessione live non disponibile: aggiornamento in polling.",
            errorCode: data.status === "failed" ? (data.error_code || "preview_failed") : prev.errorCode || "",
            liveMode: "polling",
            fallbackActive: true,
            capabilitiesState,
          }));
          handlePreviewSegments(nextSegments);
          if (data.status === "completed" || data.status === "failed") {
            pollingTimer = null;
            return;
          }
        } catch (pollError) {
          if (!isActive || controller.signal.aborted) return;
          setBatchPreview((prev) => ({
            ...prev,
            loading: false,
            error: prev.error || "Impossibile aggiornare la preview in polling.",
            errorCode: prev.errorCode || "polling_error",
            liveMode: "polling",
            fallbackActive: true,
          }));
          pollingTimer = null;
          return;
        }
        pollingTimer = window.setTimeout(poll, 1500);
      };
      poll();
    };

    const startPreview = async () => {
      setBatchPreview({
        loading: true,
        progress: 0,
        segments: [],
        scan_pages: [],
        events: [],
        error: "",
        errorCode: "",
        liveMode: "sse",
        fallbackActive: false,
      });
      try {
        const formData = new FormData();
        formData.append("source_file", file);
        formData.append("auto_match_strategy", autoMatchStrategy);
        formData.append("manifest_hint", manifestHint || "");
        formData.append("enable_ocr", ocrEnabled ? "true" : "false");
        formData.append("ocr_languages", ocrLanguages || "");
        const res = await apiClient.post("/api/hr/payslip-batches/preview-start/", formData, {
          headers: { "Content-Type": "multipart/form-data" },
          signal: controller.signal,
        });
        if (!isActive) return;
        const token = res.data?.token;
        if (!token) {
          setBatchPreview({
            loading: false,
            progress: 0,
            segments: [],
            error: "Token preview non valido.",
            errorCode: "invalid_token",
            liveMode: "sse",
            fallbackActive: false,
          });
          return;
        }
        const apiBase = (apiClient.defaults.baseURL || window.location.origin).replace(/\/$/, "");
        eventSource = new EventSource(`${apiBase}/api/hr/payslip-batches/preview-stream/${token}`, {
          withCredentials: true,
        });

        eventSource.addEventListener("progress", (event) => {
          if (!isActive) return;
          try {
            const data = JSON.parse(event.data);
            const previewPayload = data.preview || {};
            const nextSegments = enrichSegmentsWithPreviewPages(previewPayload.segments ?? [], previewPayload.scan_pages ?? []);
            const capabilitiesState = buildCapabilitiesState(data.capabilities || previewPayload.capabilities || {});
            setBatchPreview((prev) => ({
              ...prev,
              ...previewPayload,
              loading: data.status === "running" || data.status === "queued",
              progress: data.progress_percent ?? prev.progress ?? 0,
              error:
                data.status === "failed"
                  ? data.error_message || prev.error || "Preview fallita."
                  : prev.error || "",
              errorCode: data.status === "failed" ? (data.error_code || "preview_failed") : "",
              liveMode: "sse",
              fallbackActive: false,
              capabilitiesState,
            }));
            handlePreviewSegments(nextSegments);
            if (data.status === "completed" || data.status === "failed") {
              eventSource?.close();
            }
          } catch (streamError) {
            console.error("Errore parsing stream preview", streamError);
            setBatchPreview((prev) => ({
              ...prev,
              loading: false,
              progress: 0,
              error: prev.error || "Errore lettura anteprima in tempo reale.",
              errorCode: prev.errorCode || "stream_parse_error",
              liveMode: "sse",
              fallbackActive: false,
            }));
            eventSource?.close();
          }
        });

        eventSource.addEventListener("error", () => {
          if (!isActive) return;
          eventSource?.close();
          setBatchPreview((prev) => ({
            ...prev,
            error: prev.error || "Connessione live interrotta: passo al polling automatico.",
            errorCode: prev.errorCode || "stream_disconnected",
            liveMode: "polling",
            fallbackActive: true,
          }));
          apiClient.post("/api/hr/payslip-batches/preview-fallback/", { token, reason: "sse_error" }).catch(() => {});
          startPolling(token);
        });
      } catch (err) {
        if (!isActive || controller.signal.aborted) return;
        const classified = classifyPreviewError(err);
        setBatchPreview({
          loading: false,
          progress: 0,
          segments: [],
          error: classified.message,
          errorCode: classified.code,
          liveMode: "idle",
          fallbackActive: false,
        });
      }
    };

    const timeout = setTimeout(startPreview, 350);

    return () => {
      isActive = false;
      controller.abort();
      clearTimeout(timeout);
      eventSource?.close();
      if (pollingTimer) {
        clearTimeout(pollingTimer);
      }
    };
  }, [
    sourceFile,
    autoMatchStrategy,
    manifestHint,
    ocrEnabled,
    ocrLanguages,
    previewLocked,
    setBatchPreview,
    handlePreviewSegments,
  ]);
}
