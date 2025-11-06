/**
 * Full Document View Modal
 * Shows complete document content in an overlay modal
 */

import { X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

interface DocumentModalProps {
  documentId: number;
  fileName: string;
  onClose: () => void;
}

async function fetchFullDocument(documentId: number) {
  // Direct connection to backend using IPv4
  const response = await fetch(`http://127.0.0.1:8000/api/documents/${documentId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch document');
  }
  return response.json();
}

export default function DocumentModal({ documentId, fileName, onClose }: DocumentModalProps) {
  const { data: document, isLoading, error } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => fetchFullDocument(documentId),
    staleTime: 60 * 60 * 1000, // Cache for 1 hour
  });

  // Close on Escape key
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 id="modal-title" className="text-xl font-semibold text-gray-900 truncate">
            {fileName}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors p-1 rounded-lg hover:bg-gray-100"
            aria-label="Close modal"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <span className="ml-4 text-gray-600">Loading document...</span>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <p className="text-red-800 font-medium text-lg">Failed to load document</p>
              <p className="text-red-600 mt-2">
                {error instanceof Error ? error.message : 'Unknown error occurred'}
              </p>
            </div>
          )}

          {document && (
            <div className="space-y-6">
              {/* Document Metadata */}
              <div className="bg-gray-50 rounded-lg p-4 grid grid-cols-2 gap-4">
                <div>
                  <span className="text-sm font-medium text-gray-600">Category:</span>
                  <span className="ml-2 text-sm text-gray-900">{document.category}</span>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-600">File Type:</span>
                  <span className="ml-2 text-sm text-gray-900">{document.file_type}</span>
                </div>
                {document.page_count && (
                  <div>
                    <span className="text-sm font-medium text-gray-600">Pages:</span>
                    <span className="ml-2 text-sm text-gray-900">{document.page_count}</span>
                  </div>
                )}
                {document.author && (
                  <div>
                    <span className="text-sm font-medium text-gray-600">Author:</span>
                    <span className="ml-2 text-sm text-gray-900">{document.author}</span>
                  </div>
                )}
              </div>

              {/* Full Document Content */}
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Full Content</h3>
                <div className="prose prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-gray-700 leading-relaxed">
                    {document.full_content || document.content_preview || 'No content available'}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t bg-gray-50">
          <a
            href={`http://127.0.0.1:8000/api/download/${documentId}`}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            download
          >
            Download Original
          </a>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
