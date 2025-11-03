// components/ImageUploader.tsx
import React, { useRef, useState } from "react";
import { validateImage } from "../utils/validation";

interface ImageUploaderProps {
  onUpload: (file: File) => void;
  onError: (error: string) => void;
  disabled?: boolean;
}

const ImageUploader: React.FC<ImageUploaderProps> = ({ 
  onUpload, 
  onError, 
  disabled = false 
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const processFile = (file: File) => {
    const validation = validateImage(file);
    if (!validation.valid) {
      onError(validation.error!);
      return;
    }
    onUpload(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (!selectedFiles || selectedFiles.length === 0) return;
    
    processFile(selectedFiles[0]);
    e.target.value = '';
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    
    if (disabled) return;
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      processFile(droppedFiles[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  return (
    <div
      className={`w-full border-2 border-dashed rounded-md p-6 text-center transition cursor-pointer
        ${disabled 
          ? 'border-gray-200 bg-gray-50 cursor-not-allowed' 
          : isDragOver 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 hover:border-blue-400'
        }`}
      onClick={() => !disabled && fileInputRef.current?.click()}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <p className={`${disabled ? 'text-gray-400' : 'text-gray-500'}`}>
        {disabled 
          ? 'Please wait...' 
          : 'Drag & drop an image here or click to upload'
        }
      </p>
      <p className="text-xs text-gray-400 mt-1">
        PNG, JPEG only • Max 10MB
      </p>
      <input
        ref={fileInputRef}
        type="file"
        accept=".png,.jpg,.jpeg,image/png,image/jpeg"
        onChange={handleFileChange}
        disabled={disabled}
        className="hidden"
      />
    </div>
  );
};

export default ImageUploader;