// components/ImagePreview.tsx
import React, { useEffect, useState } from "react";

interface Props {
  file: File;
  result: Blob | null;
}

const ImagePreview: React.FC<Props> = ({ file, result }) => {
  const [previewUrl, setPreviewUrl] = useState<string>('');
  const [resultUrl, setResultUrl] = useState<string>('');

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    if (result) {
      const url = URL.createObjectURL(result);
      setResultUrl(url);
      
      return () => URL.revokeObjectURL(url);
    } else {
      setResultUrl('');
    }
  }, [result]);

  return (
    <div className="border p-2 rounded shadow-sm">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-medium mb-2">Original</h4>
          <img
            src={previewUrl}
            alt={file.name}
            className="w-full h-auto object-contain max-h-60 border rounded"
          />
        </div>
        
        {result && (
          <div>
            <h4 className="text-sm font-medium mb-2">Translated</h4>
            <img
              src={resultUrl}
              alt="Translated result"
              className="w-full h-auto object-contain max-h-60 border rounded"
            />
          </div>
        )}
      </div>
      
      <div className="mt-2 text-xs text-gray-500">
        File: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
      </div>
    </div>
  );
};

export default ImagePreview;