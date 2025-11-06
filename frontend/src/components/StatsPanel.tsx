/**
 * ============================================================================
 * STATS PANEL COMPONENT
 * ============================================================================
 *
 * PURPOSE:
 *   Displays system statistics and document collection overview.
 *   Gives users insight into the document database.
 *
 * FEATURES:
 *   - Total document count
 *   - Category breakdown with visual bars
 *   - Storage usage
 *   - Processing performance metrics
 *   - System health status
 *
 * AUTHOR: AI Document Pipeline Team
 * LAST UPDATED: October 2025
 */

import {
  FileText, Folder, HardDrive, Zap, Activity,
  TrendingUp, Clock, CheckCircle, AlertCircle, XCircle
} from 'lucide-react';
import type { Stats } from '../types';
import { formatBytes, formatDuration, formatDate } from '../utils';

interface StatsPanelProps {
  /** System statistics */
  stats: Stats;
}

/**
 * StatsPanel Component
 *
 * Displays a comprehensive overview of the document collection
 * and system performance.
 */
export default function StatsPanel({ stats }: StatsPanelProps) {
  // ==========================================================================
  // DERIVED VALUES
  // ==========================================================================

  /**
   * Get health status color and icon
   */
  const getHealthDisplay = () => {
    switch (stats.status) {
      case 'healthy':
        return {
          color: 'text-green-600 bg-green-50',
          icon: <CheckCircle className="w-5 h-5" />,
          text: 'Healthy',
        };
      case 'degraded':
        return {
          color: 'text-yellow-600 bg-yellow-50',
          icon: <AlertCircle className="w-5 h-5" />,
          text: 'Degraded',
        };
      case 'down':
        return {
          color: 'text-red-600 bg-red-50',
          icon: <XCircle className="w-5 h-5" />,
          text: 'Down',
        };
      default:
        return {
          color: 'text-gray-600 bg-gray-50',
          icon: <Activity className="w-5 h-5" />,
          text: 'Unknown',
        };
    }
  };

  /**
   * Calculate category percentages for visualization
   */
  const getCategoryStats = () => {
    const total = stats.total_documents;
    if (total === 0) return [];

    return Object.entries(stats.categories)
      .map(([category, count]) => ({
        category,
        count,
        percentage: (count / total) * 100,
      }))
      .sort((a, b) => b.count - a.count); // Sort by count descending
  };

  /**
   * Get color for category bar
   */
  const getCategoryColor = (category: string): string => {
    const colors: Record<string, string> = {
      invoice: 'bg-blue-500',
      contract: 'bg-purple-500',
      receipt: 'bg-green-500',
      report: 'bg-orange-500',
      other: 'bg-gray-500',
    };
    return colors[category.toLowerCase()] || colors.other;
  };

  const health = getHealthDisplay();
  const categoryStats = getCategoryStats();

  // ==========================================================================
  // RENDER
  // ==========================================================================

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          {/* Total Documents */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Documents</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {stats.total_documents.toLocaleString()}
                </p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </div>

          {/* Categories */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Categories</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {Object.keys(stats.categories).length}
                </p>
              </div>
              <div className="p-3 bg-purple-100 rounded-lg">
                <Folder className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </div>

          {/* Storage Used */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Storage Used</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {formatBytes(stats.total_storage_bytes, 0)}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <HardDrive className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>

          {/* Avg Processing Time */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Process Time</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {formatDuration(stats.avg_processing_time_ms)}
                </p>
              </div>
              <div className="p-3 bg-orange-100 rounded-lg">
                <Zap className="w-6 h-6 text-orange-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Category Breakdown */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-gray-700" />
            <h3 className="text-lg font-semibold text-gray-900">Document Categories</h3>
          </div>

          <div className="space-y-3">
            {categoryStats.map(({ category, count, percentage }) => (
              <div key={category}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="font-medium text-gray-700 capitalize">
                    {category}
                  </span>
                  <span className="text-gray-600">
                    {count.toLocaleString()} ({percentage.toFixed(1)}%)
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${getCategoryColor(category)}`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* System Status */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Health Status */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-5 h-5 text-gray-700" />
              <h3 className="text-lg font-semibold text-gray-900">System Health</h3>
            </div>

            <div className={`flex items-center gap-3 p-4 rounded-lg ${health.color}`}>
              {health.icon}
              <div>
                <p className="font-semibold">{health.text}</p>
                <p className="text-sm opacity-75">All systems operational</p>
              </div>
            </div>
          </div>

          {/* Last Updated */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center gap-2 mb-3">
              <Clock className="w-5 h-5 text-gray-700" />
              <h3 className="text-lg font-semibold text-gray-900">Last Updated</h3>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">
                {formatDate(stats.last_updated, true)}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                Most recent document processed
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
