/**
 * Full Document View Modal
 * Shows complete document content in an overlay modal
 *
 * Features:
 * - Native PDF viewing for PDF files
 * - Word document rendering with docx-preview
 * - Text view for extracted content
 * - Toggle between views
 * - Download original file
 */

import { useState, useEffect, useRef } from 'react';
import { X, FileText, Eye, Maximize2, Minimize2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { renderAsync } from 'docx-preview';
import '../docx-preview.css';

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
  // Determine if file is viewable inline (PDF, images, Word docs)
  const isPDF = fileName.toLowerCase().endsWith('.pdf');
  const isImage = /\.(jpg|jpeg|png|gif|bmp|webp)$/i.test(fileName);
  const isWord = /\.(docx)$/i.test(fileName); // Only .docx supported by docx-preview
  const isExcel = /\.(xls|xlsx)$/i.test(fileName);
  const isPowerPoint = /\.(ppt|pptx)$/i.test(fileName);
  const canShowOriginal = isPDF || isImage || isWord || isExcel || isPowerPoint;

  // Default to 'original' view for PDFs, images, and Office docs, 'text' for others
  const [viewMode, setViewMode] = useState<'text' | 'original'>(
    isPDF || isImage || isWord || isExcel || isPowerPoint ? 'original' : 'text'
  );

  // Fullscreen state
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Ref for Word document container
  const wordContainerRef = useRef<HTMLDivElement>(null);
  const [wordDocLoading, setWordDocLoading] = useState(false);
  const [wordDocError, setWordDocError] = useState<string | null>(null);
  const [wordDocRendered, setWordDocRendered] = useState(false);
  const [containerMounted, setContainerMounted] = useState(false);

  const { data: document, isLoading, error } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => fetchFullDocument(documentId),
    staleTime: 60 * 60 * 1000, // Cache for 1 hour
  });

  // Load Word document when modal opens and container is available
  useEffect(() => {
    if (isWord && viewMode === 'original' && containerMounted && wordContainerRef.current) {
      // Check if container is empty (needs rendering)
      const needsRendering = !wordContainerRef.current.innerHTML || wordContainerRef.current.innerHTML.trim() === '';

      if (needsRendering && !wordDocLoading) {
        setWordDocLoading(true);
        setWordDocError(null);

        console.log('Fetching Word document:', documentId);

        // Fetch the docx file as blob
        fetch(`http://127.0.0.1:8000/api/download/${documentId}`)
          .then(response => {
            console.log('Fetch response:', response.status, response.headers.get('content-type'));
            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.blob();
          })
          .then(blob => {
            console.log('Blob received:', blob.size, 'bytes, type:', blob.type);

            if (wordContainerRef.current) {
              // Clear previous content
              wordContainerRef.current.innerHTML = '';
              console.log('Container cleared, about to render. Container:', wordContainerRef.current);

              // Render the Word document with simpler options
              return renderAsync(blob, wordContainerRef.current);
            }
          })
          .then(() => {
            console.log('Word document rendered successfully');
            if (wordContainerRef.current) {
              console.log('Container after render - innerHTML length:', wordContainerRef.current.innerHTML.length);
              console.log('Container after render - children count:', wordContainerRef.current.children.length);
              console.log('First 500 chars of rendered HTML:', wordContainerRef.current.innerHTML.substring(0, 500));
            }
            setWordDocLoading(false);
            setWordDocRendered(true);
          })
          .catch((err) => {
            console.error('Error rendering Word document:', err);
            setWordDocError(`Failed to render Word document: ${err.message}`);
            setWordDocLoading(false);
          });
      }
    }
  }, [isWord, viewMode, containerMounted, documentId, wordDocLoading]);

  // Close on Escape key
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div
      className={`fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center ${isFullscreen ? 'p-0' : 'p-4'}`}
      onClick={onClose}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className={`bg-white shadow-xl flex flex-col overflow-hidden ${
          isFullscreen
            ? 'w-full h-full'
            : 'rounded-lg max-w-4xl w-full max-h-[90vh]'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header - Sticky */}
        <div className="flex items-center justify-between p-6 border-b bg-white sticky top-0 z-10 flex-shrink-0">
          <div className="flex-1 min-w-0">
            <h2 id="modal-title" className="text-xl font-semibold text-gray-900 truncate">
              {fileName}
            </h2>

            {/* View Mode Toggle - Show for all file types */}
            {document && (
              <div className="flex items-center gap-2 mt-3">
                <button
                  onClick={() => setViewMode('text')}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    viewMode === 'text'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <FileText className="w-4 h-4" />
                  Extracted Text
                </button>
                <button
                  onClick={() => setViewMode('original')}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    viewMode === 'original'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <Eye className="w-4 h-4" />
                  {isPDF ? 'Original PDF' :
                   isImage ? 'Original Image' :
                   isWord ? 'Original Word Doc' :
                   isExcel ? 'Original Excel' :
                   isPowerPoint ? 'Original PowerPoint' :
                   'Original Document'}
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 ml-4">
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="text-gray-500 hover:text-gray-700 transition-colors p-1 rounded-lg hover:bg-gray-100"
              aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
              title={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
            >
              {isFullscreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
            </button>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 transition-colors p-1 rounded-lg hover:bg-gray-100"
              aria-label="Close modal"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Modal Body - Scrollable */}
        <div className="flex-1 overflow-y-auto p-6 min-h-0">
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

              {/* Content Display - Toggle between text and original */}
              {viewMode === 'text' ? (
                /* Extracted Text View */
                <div className="bg-white border border-gray-200 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Extracted Text Content</h3>
                  <div className="prose prose-sm max-w-none">
                    <pre className="whitespace-pre-wrap font-sans text-gray-700 leading-relaxed">
                      {document.full_content || document.content_preview || 'No content available'}
                    </pre>
                  </div>
                </div>
              ) : (
                /* Original Document View */
                <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                  <div className="bg-gray-100 px-4 py-3 border-b border-gray-200">
                    <h3 className="text-lg font-semibold text-gray-900">Original Document</h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {isPDF && "PDF viewer - Use browser controls to zoom and navigate"}
                      {isImage && "Image viewer - Click to view full size"}
                      {isWord && "Word document viewer - Rendered with formatting preserved"}
                      {isExcel && "Extracted text preview - Download for original Excel formatting"}
                      {isPowerPoint && "Extracted text preview - Download for original PowerPoint formatting"}
                      {!isPDF && !isImage && !isWord && !isExcel && !isPowerPoint && "Document preview - Download to view in native application"}
                    </p>
                  </div>

                  {/* PDF Viewer */}
                  {isPDF && (
                    <iframe
                      src={`http://127.0.0.1:8000/api/download/${documentId}#view=FitH`}
                      className="w-full h-[600px] border-0"
                      title={`PDF viewer - ${fileName}`}
                    />
                  )}

                  {/* Image Viewer */}
                  {isImage && (
                    <div className="flex items-center justify-center bg-gray-50 p-6">
                      <img
                        src={`http://127.0.0.1:8000/api/download/${documentId}`}
                        alt={fileName}
                        className="max-w-full max-h-[600px] object-contain rounded-lg shadow-lg"
                      />
                    </div>
                  )}

                  {/* Word Document Viewer with docx-preview */}
                  {isWord && (
                    <div className="bg-white">
                      {wordDocLoading && (
                        <div className="flex items-center justify-center py-12">
                          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                          <span className="ml-4 text-gray-600">Rendering Word document...</span>
                        </div>
                      )}

                      {wordDocError && (
                        <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-4">
                          <div className="flex">
                            <div className="flex-shrink-0">
                              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                              </svg>
                            </div>
                            <div className="ml-3">
                              <p className="text-sm text-red-700">{wordDocError}</p>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Word document container */}
                      <div
                        ref={(el) => {
                          wordContainerRef.current = el;
                          if (el && !containerMounted) {
                            setContainerMounted(true);
                          } else if (!el && containerMounted) {
                            // Container unmounted (switched to text view)
                            setContainerMounted(false);
                          }
                        }}
                        className="docx-wrapper p-6 bg-white border border-gray-200 rounded-lg"
                        style={{
                          minHeight: '400px',
                          backgroundColor: 'white',
                          color: 'black'
                        }}
                      />
                    </div>
                  )}

                  {/* Excel/PowerPoint - Show extracted content */}
                  {(isExcel || isPowerPoint) && (
                    <div className="bg-white">
                      {/* Note about Office document viewing */}
                      <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-4">
                        <div className="flex">
                          <div className="flex-shrink-0">
                            <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                          </div>
                          <div className="ml-3">
                            <p className="text-sm text-blue-700">
                              <strong>Office Document Preview:</strong> Showing extracted text content.
                              Download the file to view with original formatting.
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Show extracted text content */}
                      <div className="p-6 border border-gray-200 rounded-lg">
                        {document.full_content || document.content_preview ? (
                          <pre className="whitespace-pre-wrap font-sans text-gray-700 leading-relaxed text-sm">
                            {document.full_content || document.content_preview}
                          </pre>
                        ) : (
                          <div className="flex flex-col items-center justify-center p-12 text-center text-gray-500">
                            <div className="text-6xl mb-4">
                              {isExcel ? '📊' : '📊'}
                            </div>
                            <p className="text-gray-600 mb-4">No text content extracted from this document.</p>
                            <p className="text-sm text-gray-500">Download the file to view it.</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Other file types - show extracted text content */}
                  {!isPDF && !isImage && !isWord && !isExcel && !isPowerPoint && (
                    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                      <div className="bg-gray-100 px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900">Document Content (Extracted Text)</h3>
                          <p className="text-sm text-gray-600 mt-1">
                            {document.file_type?.includes('word') || document.file_type?.includes('document') ? 'Word Document - ' :
                             document.file_type?.includes('excel') || document.file_type?.includes('spreadsheet') ? 'Spreadsheet - ' :
                             document.file_type?.includes('text') ? 'Text File - ' : 'Document - '}
                            Original formatting not preserved
                          </p>
                        </div>
                        <a
                          href={`http://127.0.0.1:8000/api/download/${documentId}`}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium inline-flex items-center gap-2 text-sm"
                          download
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                          Download Original
                        </a>
                      </div>

                      {/* Show extracted text content */}
                      <div className="p-6 bg-white">
                        {document.full_content || document.content_preview ? (
                          <pre className="whitespace-pre-wrap font-sans text-gray-700 leading-relaxed text-sm">
                            {document.full_content || document.content_preview}
                          </pre>
                        ) : (
                          <div className="flex flex-col items-center justify-center p-12 text-center text-gray-500">
                            <div className="text-6xl mb-4">
                              {document.file_type?.includes('word') || document.file_type?.includes('document') ? '📝' :
                               document.file_type?.includes('excel') || document.file_type?.includes('spreadsheet') ? '📊' :
                               document.file_type?.includes('text') ? '📄' : '📎'}
                            </div>
                            <p className="text-gray-600 mb-4">No text content available for this document.</p>
                            <p className="text-sm text-gray-500">Download the original file to view it.</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer - Sticky */}
        <div className="flex items-center justify-end gap-3 p-6 border-t bg-gray-50 sticky bottom-0 flex-shrink-0">
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
