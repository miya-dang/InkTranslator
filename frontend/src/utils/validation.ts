import { API_CONFIG } from './constants';

export const validateImage = (file: File): { valid: boolean; error?: string } => {
  // Check file type
  if (!API_CONFIG.ALLOWED_TYPES.includes(file.type)) {
    return { valid: false, error: 'Only PNG and JPEG images are allowed' };
  }

  // Check file size
  if (file.size > API_CONFIG.MAX_FILE_SIZE) {
    return { valid: false, error: 'File size must be less than 10MB' };
  }

  // Check file extension
  if (file.name) {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (ext && !API_CONFIG.ALLOWED_EXTENSIONS.includes(ext)) {
      return { valid: false, error: 'Invalid file extension' };
    }
  }

  return { valid: true };
};
