// components/ImageHandler.tsx
import React, { useCallback, useState, useEffect } from "react";
import ImageUploader from "./ImageUploader";
import ImagePreview from "./ImagePreview";
import OptionsPanel from "./OptionsPanel";
import { ApiService, ApiError } from "../utils/api";

const ImageHandler: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<Blob | null>(null);
  const [sourceLanguage, setSourceLanguage] = useState("japanese");
  const [targetLanguage, setTargetLanguage] = useState("english");
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string>("");
  const [statusMessage, setStatusMessage] = useState<string>(""); // 👈 status message
  const [sessionId, setSessionId] = useState<string>("");

  // Create session ID on component mount
  useEffect(() => {
    setSessionId(ApiService.createSession());
  }, []);

  const handleFileChange = useCallback((newFile: File | null) => {
    setFile(newFile);
    setResult(null);
    setError("");
    setStatusMessage("");
  }, []);

  const handleError = useCallback((errorMessage: string) => {
    setError(errorMessage);
    setFile(null);
    setResult(null);
    setStatusMessage("");
  }, []);

  const pollStatus = useCallback(
    async (sessionId: string) => {
      const interval = setInterval(async () => {
        try {
          const status = await ApiService.getStatus(sessionId);

          if (status.message) {
            setStatusMessage(status.message);
          }

          if (status.status === "COMPLETED" || status.status === "ERROR") {
            clearInterval(interval);
          }
        } catch (err) {
          console.warn("Polling failed:", err);
          clearInterval(interval);
        }
      }, 1000);
    },
    []
  );


  const handleSubmit = useCallback(async () => {
    if (!file) return;

    setIsProcessing(true);
    setError("");
    setStatusMessage("Starting translation...");

    try {
      pollStatus(sessionId); // start polling messages

      const resultBlob = await ApiService.translateImage(
        file,
        sourceLanguage,
        targetLanguage,
        undefined, // no numeric progress callback
        sessionId
      );

      setResult(resultBlob);
      setStatusMessage("Translation complete!");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);

        if (err.status === 413) {
          setError("File too large. Please use an image smaller than 10MB.");
        } else if (err.status === 400) {
          setError("Invalid file format. Please use PNG or JPEG images only.");
        } else if (err.status === 422) {
          setError(`Processing error: ${err.message}`);
        } else if (err.type === "network_error") {
          setError("Connection failed. Please check your internet connection.");
        }
      } else {
        setError("Translation failed. Please try again.");
      }
    } finally {
      setIsProcessing(false);
    }
  }, [file, sourceLanguage, targetLanguage, sessionId, pollStatus]);

  const clearForm = useCallback(() => {
    if (isProcessing && sessionId) {
      ApiService.cancelTranslation(sessionId);
    }

    setFile(null);
    setResult(null);
    setError("");
    setStatusMessage("");
    setIsProcessing(false);
    setSessionId(ApiService.createSession());
  }, [isProcessing, sessionId]);

  const downloadResult = useCallback(() => {
    if (!result) return;

    const url = URL.createObjectURL(result);
    const a = document.createElement("a");
    a.href = url;
    a.download = `translated_${file?.name || "image.png"}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [result, file]);

  const retryTranslation = useCallback(() => {
    setError("");
    handleSubmit();
  }, [handleSubmit]);

  return (
    <div className="p-4 border rounded-md bg-white shadow-md max-w-4xl mx-auto">
      <h2 className="text-xl font-bold mb-4">Image Translation</h2>

      <ImageUploader
        onUpload={handleFileChange}
        onError={handleError}
        disabled={isProcessing}
      />

      {error && (
        <div className="mt-2 p-3 bg-red-100 border border-red-300 rounded text-red-700">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium">Error</p>
              <p className="text-sm">{error}</p>
            </div>
            {file && !isProcessing && (
              <button
                onClick={retryTranslation}
                className="ml-2 text-xs bg-red-600 text-white px-2 py-1 rounded hover:bg-red-700"
              >
                Retry
              </button>
            )}
          </div>
        </div>
      )}

      {file && (
        <div className="my-4">
          <ImagePreview file={file} result={result} />
        </div>
      )}

      <OptionsPanel
        sourceLanguage={sourceLanguage}
        targetLanguage={targetLanguage}
        onSourceLanguageChange={setSourceLanguage}
        onTargetLanguageChange={setTargetLanguage}
        disabled={isProcessing}
      />

      {isProcessing && statusMessage && (
        <div className="mt-4">
          <p className="text-sm text-gray-600">{statusMessage}</p>
          <button
            onClick={clearForm}
            className="text-xs text-red-600 hover:text-red-800 underline mt-1"
          >
            Cancel
          </button>
        </div>
      )}

      <div className="mt-4 flex gap-2 flex-wrap">
        <button
          onClick={handleSubmit}
          disabled={isProcessing || !file}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isProcessing ? "Processing..." : "Translate"}
        </button>

        {result && (
          <button
            onClick={downloadResult}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
          >
            Download
          </button>
        )}

        {(file || result) && (
          <button
            onClick={clearForm}
            disabled={isProcessing}
            className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600 disabled:opacity-50"
          >
            Clear
          </button>
        )}
      </div>

      {/* Debugging info in dev */}
      {process.env.NODE_ENV === "development" && sessionId && (
        <div className="mt-2 text-xs text-gray-400">Session: {sessionId}</div>
      )}
    </div>
  );
};

export default ImageHandler;
