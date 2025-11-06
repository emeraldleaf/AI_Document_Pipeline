/**
 * ============================================================================
 * SEARCH FILTERS COMPONENT
 * ============================================================================
 *
 * PURPOSE:
 *   Provides category filtering for search results.
 *   Allows users to narrow down results by document category.
 *
 * FEATURES:
 *   - Category pills (clickable badges)
 *   - "All" option to clear filter
 *   - Active state highlighting
 *   - Responsive layout
 *
 * AUTHOR: AI Document Pipeline Team
 * LAST UPDATED: October 2025
 */

import { Filter, X } from 'lucide-react';

interface SearchFiltersProps {
  /** Available categories to filter by */
  categories: string[];

  /** Currently selected category (undefined = all) */
  selectedCategory: string | undefined;

  /** Callback when category selection changes */
  onCategoryChange: (category: string | undefined) => void;
}

/**
 * SearchFilters Component
 *
 * Displays category filter pills. Clicking a category filters results.
 * Clicking the active category (or "All") clears the filter.
 */
export default function SearchFilters({
  categories,
  selectedCategory,
  onCategoryChange,
}: SearchFiltersProps) {
  // ==========================================================================
  // HELPERS
  // ==========================================================================

  /**
   * Handle category click
   */
  const handleCategoryClick = (category: string) => {
    if (selectedCategory === category) {
      // Clicking active category clears filter
      onCategoryChange(undefined);
    } else {
      // Select new category
      onCategoryChange(category);
    }
  };

  /**
   * Clear all filters
   */
  const handleClearFilters = () => {
    onCategoryChange(undefined);
  };

  // ==========================================================================
  // RENDER
  // ==========================================================================

  return (
    <div className="mt-4 p-4 bg-white border border-gray-200 rounded-lg">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
          <Filter className="w-4 h-4" />
          <span>Filter by Category</span>
        </div>

        {/* Clear Filters Button (only show if filter is active) */}
        {selectedCategory && (
          <button
            onClick={handleClearFilters}
            className="text-xs text-gray-600 hover:text-gray-900 flex items-center gap-1"
          >
            <X className="w-3 h-3" />
            Clear
          </button>
        )}
      </div>

      {/* Category Pills */}
      <div className="flex flex-wrap gap-2">
        {/* "All" Button */}
        <button
          onClick={handleClearFilters}
          className={`px-4 py-2 rounded-full text-sm font-medium border-2 transition-all ${
            !selectedCategory
              ? 'bg-gray-800 text-white border-gray-800'
              : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100'
          }`}
        >
          All Categories
        </button>

        {/* Category Buttons */}
        {categories.map((category) => {
          const isActive = selectedCategory === category;

          return (
            <button
              key={category}
              onClick={() => handleCategoryClick(category)}
              className={`px-4 py-2 rounded-full text-sm font-medium border-2 transition-all ${
                isActive
                  ? 'bg-blue-600 text-white border-blue-600 shadow-md'
                  : 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100'
              }`}
            >
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </button>
          );
        })}
      </div>

      {/* Active Filter Indicator */}
      {selectedCategory && (
        <div className="mt-3 text-xs text-gray-600">
          Showing results for:{' '}
          <span className="font-semibold text-gray-900">
            {selectedCategory.charAt(0).toUpperCase() + selectedCategory.slice(1)}
          </span>
        </div>
      )}
    </div>
  );
}
