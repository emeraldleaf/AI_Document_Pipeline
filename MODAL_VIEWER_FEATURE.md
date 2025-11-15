# Document Modal Viewer - Feature Summary

## Overview
Enhanced the Document Modal to support viewing original documents of any type, with intelligent defaults and fallback handling.

## Features Implemented

### 1. **Dual View Mode**
The modal now has two viewing modes:
- **Extracted Text**: Shows the extracted and processed text content
- **Original Document**: Shows the actual document file

### 2. **Smart Default Behavior**
- **PDFs**: Opens in "Original PDF" mode by default → shows native PDF in iframe
- **Images** (jpg, png, gif, etc.): Opens in "Original Image" mode → displays image directly
- **Other files** (docx, txt, xlsx, etc.): Opens in "Extracted Text" mode → shows extracted content

### 3. **File Type Handling**

#### PDF Files (`.pdf`)
- Embedded PDF viewer using iframe
- Browser's native PDF controls (zoom, page navigation)
- 600px height viewer
- Falls back to download if PDF can't render

#### Image Files (`.jpg`, `.png`, `.gif`, `.bmp`, `.webp`)
- Direct image display
- Responsive sizing (max 600px height)
- Centered with shadow for better presentation
- Click to view full size in browser

#### Other Files (`.docx`, `.xlsx`, `.txt`, etc.)
- Shows helpful message explaining preview is not available
- Large file type icon (📝 for docs, 📊 for spreadsheets, 📄 for text)
- Clear instructions to download
- Prominent "Download Original File" button

### 4. **Toggle Buttons**
Two buttons in the modal header:
- **"Extracted Text"** button (with FileText icon)
- **"Original Document"** button (with Eye icon)
- Active button highlighted in blue
- Inactive button in gray with hover effect

### 5. **User Experience**
- **Metadata panel**: Shows category, file type, pages, author
- **Loading states**: Spinner while fetching document
- **Error handling**: Clear error messages if document fails to load
- **Keyboard support**: Press ESC to close modal
- **Download button**: Always available in footer
- **Responsive design**: Works on different screen sizes

## How to Use

### As a User:
1. Search for documents
2. Click the **"View Full"** button (purple) on any result card
3. The modal opens showing:
   - PDFs → Native PDF viewer
   - Images → Image display
   - Other → Extracted text with download option
4. Use the toggle buttons to switch between views:
   - **"Extracted Text"** → See the searchable text content
   - **"Original Document"** → See the actual file
5. Click **"Download Original"** to save the file
6. Press ESC or click "Close" to exit

### For Developers:
The modal component is at: `frontend/src/components/DocumentModal.tsx`

Key props:
```typescript
interface DocumentModalProps {
  documentId: number;  // Document ID from search results
  fileName: string;    // Used to determine file type
  onClose: () => void; // Callback to close modal
}
```

## Technical Details

### File Type Detection
```typescript
const isPDF = fileName.toLowerCase().endsWith('.pdf');
const isImage = /\.(jpg|jpeg|png|gif|bmp|webp)$/i.test(fileName);
```

### API Endpoints Used
- `GET /api/documents/{id}` - Fetch document metadata and content
- `GET /api/download/{id}` - Download/stream original file

### View Modes
- `text`: Shows `document.full_content` or `document.content_preview`
- `original`: Shows iframe (PDF), img tag (images), or download prompt (others)

## Benefits

1. **Flexible Viewing**: Users can see both extracted text and original formatting
2. **Better Search Experience**: See context in extracted text, verify in original
3. **Universal Support**: Handles any file type gracefully
4. **Native PDF Reading**: No need to download PDFs to read them
5. **Quick Image Preview**: See images without downloading
6. **Clear Guidance**: Users know what to do for non-previewable files

## Example Use Cases

### Use Case 1: Searching Technical Manuals (PDF)
1. Search for "API endpoints"
2. Click "View Full" on `technical_manual_20_pages.pdf`
3. Modal opens showing native PDF viewer
4. Navigate to page 6 using PDF controls
5. Toggle to "Extracted Text" to see searchable content with page markers
6. See highlighted text: `[Page 6] Chapter 5: API Endpoints...`

### Use Case 2: Invoice Images
1. Search for "Sortex invoice"
2. Click "View Full" on invoice image
3. Modal shows full-resolution image
4. Toggle to "Extracted Text" to see OCR'd text
5. Download original if needed

### Use Case 3: Word Documents
1. Search for "contract terms"
2. Click "View Full" on `.docx` file
3. Modal shows extracted text (since Word can't preview in browser)
4. Toggle to "Original Document" to see download prompt
5. Click "Download Original File" to open in Word

## Files Modified

- `frontend/src/components/DocumentModal.tsx` - Main implementation
  - Added view mode state management
  - Added file type detection
  - Added PDF iframe viewer
  - Added image viewer
  - Added download fallback for unsupported types
  - Added toggle buttons

## Testing

To test the feature:

1. **Start servers** (already running):
   ```bash
   # Backend (port 8000)
   python3 -m uvicorn api.main:app --reload

   # Frontend (port 3000)
   cd frontend && npm start
   ```

2. **Test different file types**:
   - PDF: Search "API", click "View Full" on technical manual
   - Text: Search for any .txt file
   - DOCX: Search for contract or specification files
   - Images: If you have any in your index

3. **Test toggle functionality**:
   - Click "Extracted Text" → See searchable content
   - Click "Original Document" → See native file or download prompt
   - Verify active button is highlighted

4. **Test download**:
   - Click "Download Original" button in footer
   - File should download to your browser's download folder

## Future Enhancements (Optional)

- [ ] Support for Excel/CSV preview using a data table
- [ ] Support for text files (.txt) with syntax highlighting
- [ ] Full-screen mode for PDFs
- [ ] Zoom controls for images
- [ ] Page jump for PDFs (e.g., "Jump to Page 6" from search results)
- [ ] Thumbnail navigation for multi-page PDFs
- [ ] Compare mode (side-by-side extracted text and original)

## Browser Compatibility

- **Chrome/Edge**: Full support (PDF iframe works natively)
- **Firefox**: Full support (PDF iframe works natively)
- **Safari**: Full support (PDF iframe works natively)
- **Mobile browsers**: Basic support (may prompt to download PDFs)

## Troubleshooting

### PDF doesn't show in iframe
- **Cause**: Browser security settings or CORS issues
- **Solution**: Download button is always available as fallback

### Image doesn't load
- **Cause**: File path issue or missing file
- **Solution**: Check backend logs, verify file exists

### Download button doesn't work
- **Cause**: Backend not running or CORS issue
- **Solution**: Verify backend is running on port 8000

---

**Status**: ✅ Implemented and Ready to Use
**Last Updated**: November 6, 2025
