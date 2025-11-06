/**
 * ============================================================================
 * SEARCH RESULT CARD COMPONENT
 * ============================================================================
 *
 * PURPOSE:
 *   Displays a single search result with all relevant information
 *   and actions (preview, download, full view modal).
 *
 * FEATURES:
 *   - Document metadata (filename, category, date)
 *   - Relevance score with visual indicator
 *   - Highlighted text snippets
 *   - Preview, full view modal, and download buttons
 *   - File size and page count
 *   - Responsive design
 *
 * AUTHOR: AI Document Pipeline Team
 * LAST UPDATED: November 2025
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Download, Eye, Calendar, HardDrive,
  FileType, TrendingUp, FileText
} from 'lucide-react';
import type { SearchResult, SearchMode } from '../types';
import { formatBytes, formatDate, truncateText } from '../utils';
import { downloadDocument, getDocumentPreview } from '../api';
import DocumentModal from './DocumentModal';

interface SearchResultCardProps {
  /** The search result to display */
  result: SearchResult;

  /** Current search mode (affects how score is displayed) */
  searchMode?: SearchMode;
}

/**
 * SearchResultCard Component
 *
 * Displays a single document from search results.
 * Clicking the card expands it to show more details.
 */
export default function SearchResultCard({ result }: SearchResultCardProps) {
  // ==========================================================================
  // STATE
  // ==========================================================================

  const [isExpanded, setIsExpanded] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [showModal, setShowModal] = useState(false);

  // ==========================================================================
  // DATA FETCHING - TANSTACK QUERY (Lazy Loading Pattern)
  // ==========================================================================

  const {
    data: previewText,
    isLoading: isLoadingPreview,
    error: previewError,
  } = useQuery({
    queryKey: ['preview', result.id],
    queryFn: () => getDocumentPreview(result.id.toString()),
    enabled: showPreview,
    staleTime: 60 * 60 * 1000,
    retry: 1,
  });

  // ==========================================================================
  // EVENT HANDLERS
  // ==========================================================================

  /**
   * Open full document modal
   */
  const handleViewFull = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowModal(true);
  };

  /**
   * Toggle preview visibility
   */
  const handlePreview = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowPreview(!showPreview);
  };

  /**
   * Download document
   */
  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    downloadDocument(result.id.toString());
  };

  /**
   * Toggle card expansion
   */
  const handleCardClick = () => {
    setIsExpanded(!isExpanded);
  };

  // ==========================================================================
  // DERIVED VALUES
  // ==========================================================================

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-600 bg-green-50';
    if (score >= 0.5) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const getFileIcon = () => {
    const type = result.metadata.file_type.toLowerCase();
    if (type.includes('pdf')) return '📄';
    if (type.includes('doc')) return '📝';
    if (type.includes('xls') || type.includes('csv')) return '📊';
    if (type.includes('image') || type.includes('png') || type.includes('jpg')) return '🖼️';
    return '📎';
  };

  const getCategoryColor = (category: string): string => {
    const colors: Record<string, string> = {
      invoice: 'bg-blue-100 text-blue-800',
      contract: 'bg-purple-100 text-purple-800',
      receipt: 'bg-green-100 text-green-800',
      report: 'bg-orange-100 text-orange-800',
      research: 'bg-pink-100 text-pink-800',
      compliance: 'bg-indigo-100 text-indigo-800',
      correspondence: 'bg-cyan-100 text-cyan-800',
      other: 'bg-gray-100 text-gray-800',
    };
    return colors[category.toLowerCase()] || colors.other;
  };

  // ==========================================================================
  // RENDER
  // ==========================================================================

  return (
    <div
      className={`bg-white border-2 rounded-lg shadow-sm hover:shadow-md transition-all cursor-pointer ${
        isExpanded ? 'border-blue-400' : 'border-gray-200'
      }`}
      onClick={handleCardClick}
    >
      {/* Card Header */}
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          {/* Left: Document Info */}
          <div className="flex-1 min-w-0">
            {/* Filename and Category */}
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl flex-shrink-0">{getFileIcon()}</span>
              <h3 className="text-lg font-semibold text-gray-900 truncate">
                {result.file_name}
              </h3>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(result.category)}`}>
                {result.category}
              </span>
            </div>

            {/* Metadata Row */}
            <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {result.metadata.modified_date ? formatDate(result.metadata.modified_date) : 'N/A'}
              </span>
              <span className="flex items-center gap-1">
                <HardDrive className="w-4 h-4" />
                {formatBytes(result.metadata.file_size)}
              </span>
              {result.metadata.page_count && (
                <span className="flex items-center gap-1">
                  <FileType className="w-4 h-4" />
                  {result.metadata.page_count} {result.metadata.page_count === 1 ? 'page' : 'pages'}
                </span>
              )}
            </div>

            {/* Content Preview - Now shows matching snippet with context */}
            <div className="text-sm text-gray-700 bg-gray-50 border-l-4 border-blue-400 p-3 rounded">
              <p className="whitespace-pre-wrap">
                {truncateText(result.content_preview, isExpanded ? 1000 : 200)}
              </p>
            </div>
          </div>

          {/* Right: Score and Actions */}
          <div className="flex flex-col items-end gap-3">
            {/* Relevance Score */}
            <div className={`px-3 py-2 rounded-lg flex items-center gap-2 ${getScoreColor(result.combined_score)}`}>
              <TrendingUp className="w-4 h-4" />
              <span className="font-semibold">{result.combined_score.toFixed(3)}</span>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col gap-2">
              <button
                onClick={handleViewFull}
                className="px-4 py-2 bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100 transition-colors flex items-center gap-2 text-sm font-medium"
              >
                <FileText className="w-4 h-4" />
                View Full
              </button>

              <button
                onClick={handlePreview}
                disabled={isLoadingPreview}
                className="px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors flex items-center gap-2 text-sm font-medium disabled:opacity-50"
              >
                <Eye className="w-4 h-4" />
                {isLoadingPreview ? 'Loading...' : 'Preview'}
              </button>

              <button
                onClick={handleDownload}
                className="px-4 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors flex items-center gap-2 text-sm font-medium"
              >
                <Download className="w-4 h-4" />
                Download
              </button>
            </div>
          </div>
        </div>

        {/* Preview Modal (TanStack Query powered) */}
        {showPreview && (
          <div className="mt-4 border-t pt-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-gray-900">Document Preview</h4>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowPreview(false);
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                Close
              </button>
            </div>

            {isLoadingPreview && (
              <div className="flex items-center justify-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-3 text-gray-600">Loading preview...</span>
              </div>
            )}

            {previewError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-800 font-medium">Failed to load preview</p>
                <p className="text-red-600 text-sm mt-1">
                  {previewError instanceof Error ? previewError.message : 'Unknown error'}
                </p>
              </div>
            )}

            {previewText && (
              <div className="max-h-96 overflow-y-auto bg-white border border-gray-200 rounded-lg p-4 custom-scrollbar">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
                  {previewText}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Expand/Collapse Indicator */}
        <div className="mt-4 text-center text-xs text-gray-500">
          {isExpanded ? '▲ Click to collapse' : '▼ Click to expand'}
        </div>
      </div>

      {/* Full Document Modal */}
      {showModal && (
        <DocumentModal
          documentId={result.id}
          fileName={result.file_name}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}
