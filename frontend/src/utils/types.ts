export interface Language {
  code: string;
  name: string;
  source_only?: boolean;
}

export interface TranslationRequest {
  source_language: string;
  target_language: string;
}

export interface ApiErrorInterface {
  error: string;
  detail: string;
  type?: string;
  status_code?: number;
}

export interface SupportedLanguagesResponse {
  languages: Language[];
  max_file_size_mb: number;
  allowed_formats: string[];
}

export type ProcessingStage =
  | "INITIALIZED"
  | "OCR"
  | "TRANSLATION"
  | "INPAINTING"
  | "RENDERING"
  | "COMPLETED"
  | "ERROR";

export interface ProcessingStatusResponse {
  job_id: string;          // ✅ matches backend
  status: ProcessingStage; // ✅ step enum
  message: string;         // ✅ step description
  timestamp?: string;
}