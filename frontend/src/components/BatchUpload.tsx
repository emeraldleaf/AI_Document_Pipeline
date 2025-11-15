import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

interface UploadProgress {
  current: number;
  total: number;
  currentFile: string;
  status: 'idle' | 'uploading' | 'processing' | 'complete' | 'error';
}

interface ProcessedDoc {
  filename: string;
  success: boolean;
  category?: string;
  error?: string;
  confidence?: number;
  task_id?: string;
}

interface BatchProgress {
  batch_id: string;
  current: number;
  total: number;
  currentFile: string;
  percent: number;
  successCount: number;
  failureCount: number;
  results: ProcessedDoc[];
}

export function BatchUpload() {
  const [progress, setProgress] = useState<UploadProgress>({
    current: 0,
    total: 0,
    currentFile: '',
    status: 'idle'
  });
  const [results, setResults] = useState<ProcessedDoc[]>([]);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'upload' | 'results' | 'stats'>('upload');
  const [ws, setWs] = useState<WebSocket | null>(null);

  console.log('BatchUpload component rendering', { progress, results, batchId, activeTab });

  // Connect to WebSocket for real-time progress
  const connectWebSocket = useCallback((batchId: string) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/batch-progress/${batchId}`;
    const websocket = new WebSocket(wsUrl);

    websocket.onmessage = (event) => {
      const data: BatchProgress = JSON.parse(event.data);
      setProgress({
        current: data.current,
        total: data.total,
        currentFile: data.currentFile,
        status: data.current >= data.total ? 'complete' : 'processing'
      });
      setResults(data.results);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    websocket.onclose = () => {
      console.log('WebSocket connection closed');
    };

    setWs(websocket);
  }, []);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setProgress({
      current: 0,
      total: acceptedFiles.length,
      currentFile: '',
      status: 'uploading'
    });
    setResults([]);
    setActiveTab('results');

    try {
      // Create batch submission
      const formData = new FormData();
      acceptedFiles.forEach((file) => {
        formData.append('files', file);
      });

      const response = await fetch('http://localhost:8000/api/batch-upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      setBatchId(data.batch_id);

      // Connect WebSocket for progress tracking
      connectWebSocket(data.batch_id);

      setProgress(prev => ({
        ...prev,
        status: 'processing'
      }));

    } catch (error) {
      console.error('Upload error:', error);
      setProgress(prev => ({
        ...prev,
        status: 'error'
      }));
    }
  }, [connectWebSocket]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt']
    }
  });

  const successCount = results.filter(r => r.success).length;
  const failureCount = results.filter(r => !r.success).length;
  const percent = progress.total > 0 ? (progress.current / progress.total) * 100 : 0;

  return (
    <div className="batch-upload-container" style={{ padding: '2rem', minHeight: '500px', backgroundColor: 'white', borderRadius: '8px' }}>
      <h1 style={{ marginBottom: '1rem', fontSize: '24px', fontWeight: 'bold' }}>Batch Document Upload</h1>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', borderBottom: '2px solid #e5e7eb' }}>
        <button
          onClick={() => setActiveTab('upload')}
          style={{
            padding: '0.5rem 1rem',
            border: 'none',
            background: 'transparent',
            borderBottom: activeTab === 'upload' ? '3px solid #3b82f6' : 'none',
            fontWeight: activeTab === 'upload' ? 'bold' : 'normal',
            cursor: 'pointer'
          }}
        >
          Upload
        </button>
        <button
          onClick={() => setActiveTab('results')}
          style={{
            padding: '0.5rem 1rem',
            border: 'none',
            background: 'transparent',
            borderBottom: activeTab === 'results' ? '3px solid #3b82f6' : 'none',
            fontWeight: activeTab === 'results' ? 'bold' : 'normal',
            cursor: 'pointer'
          }}
        >
          Results {results.length > 0 && `(${results.length})`}
        </button>
        <button
          onClick={() => setActiveTab('stats')}
          style={{
            padding: '0.5rem 1rem',
            border: 'none',
            background: 'transparent',
            borderBottom: activeTab === 'stats' ? '3px solid #3b82f6' : 'none',
            fontWeight: activeTab === 'stats' ? 'bold' : 'normal',
            cursor: 'pointer'
          }}
        >
          Statistics
        </button>
      </div>

      {/* Upload Tab */}
      {activeTab === 'upload' && (
        <div>
          <div
            {...getRootProps()}
            style={{
              border: '2px dashed #3b82f6',
              borderRadius: '8px',
              padding: '3rem',
              textAlign: 'center',
              cursor: 'pointer',
              backgroundColor: isDragActive ? '#eff6ff' : '#f9fafb'
            }}
          >
            <input {...getInputProps()} />
            {isDragActive ? (
              <p style={{ fontSize: '1.2rem', color: '#3b82f6' }}>Drop files here...</p>
            ) : (
              <div>
                <p style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>
                  Drag & drop documents here, or click to select
                </p>
                <p style={{ color: '#6b7280', fontSize: '0.9rem' }}>
                  Supports PDF, DOC, DOCX, TXT files
                </p>
              </div>
            )}
          </div>

          {/* Progress Bar */}
          {progress.status !== 'idle' && (
            <div style={{ marginTop: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 'bold' }}>
                  {progress.status === 'uploading' && 'Uploading files...'}
                  {progress.status === 'processing' && `Processing: ${progress.currentFile}`}
                  {progress.status === 'complete' && 'Complete!'}
                  {progress.status === 'error' && 'Error occurred'}
                </span>
                <span>{Math.round(percent)}%</span>
              </div>
              <div style={{
                width: '100%',
                height: '24px',
                backgroundColor: '#e5e7eb',
                borderRadius: '12px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${percent}%`,
                  height: '100%',
                  backgroundColor: progress.status === 'error' ? '#ef4444' : '#3b82f6',
                  transition: 'width 0.3s ease'
                }} />
              </div>
              <div style={{ marginTop: '0.5rem', color: '#6b7280' }}>
                {progress.current} / {progress.total} documents processed
              </div>
            </div>
          )}
        </div>
      )}

      {/* Results Tab */}
      {activeTab === 'results' && (
        <div>
          {results.length === 0 ? (
            <p style={{ color: '#6b7280' }}>No results yet. Upload documents to see results here.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {results.map((result, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '1rem',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    backgroundColor: result.success ? '#f0fdf4' : '#fef2f2'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>
                        {result.filename}
                      </div>
                      {result.success ? (
                        <div style={{ color: '#16a34a' }}>
                          Category: {result.category}
                          {result.confidence && ` (${(result.confidence * 100).toFixed(1)}% confidence)`}
                        </div>
                      ) : (
                        <div style={{ color: '#dc2626' }}>
                          Error: {result.error}
                        </div>
                      )}
                    </div>
                    <div style={{
                      padding: '0.25rem 0.75rem',
                      borderRadius: '4px',
                      fontSize: '0.875rem',
                      fontWeight: 'bold',
                      backgroundColor: result.success ? '#16a34a' : '#dc2626',
                      color: 'white'
                    }}>
                      {result.success ? 'SUCCESS' : 'FAILED'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Statistics Tab */}
      {activeTab === 'stats' && (
        <div>
          {results.length === 0 ? (
            <p style={{ color: '#6b7280' }}>No statistics yet. Upload documents to see statistics here.</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
              <div style={{
                padding: '1.5rem',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                backgroundColor: '#f9fafb'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3b82f6' }}>
                  {results.length}
                </div>
                <div style={{ color: '#6b7280', marginTop: '0.5rem' }}>Total Documents</div>
              </div>
              <div style={{
                padding: '1.5rem',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                backgroundColor: '#f0fdf4'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#16a34a' }}>
                  {successCount}
                </div>
                <div style={{ color: '#6b7280', marginTop: '0.5rem' }}>Successful</div>
              </div>
              <div style={{
                padding: '1.5rem',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                backgroundColor: '#fef2f2'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#dc2626' }}>
                  {failureCount}
                </div>
                <div style={{ color: '#6b7280', marginTop: '0.5rem' }}>Failed</div>
              </div>
              <div style={{
                padding: '1.5rem',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                backgroundColor: '#f9fafb'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3b82f6' }}>
                  {results.length > 0 ? ((successCount / results.length) * 100).toFixed(1) : 0}%
                </div>
                <div style={{ color: '#6b7280', marginTop: '0.5rem' }}>Success Rate</div>
              </div>
            </div>
          )}

          {/* Category Breakdown */}
          {results.length > 0 && (
            <div style={{ marginTop: '2rem' }}>
              <h3 style={{ marginBottom: '1rem' }}>Category Breakdown</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {Object.entries(
                  results
                    .filter(r => r.success && r.category)
                    .reduce((acc, r) => {
                      acc[r.category!] = (acc[r.category!] || 0) + 1;
                      return acc;
                    }, {} as Record<string, number>)
                ).map(([category, count]) => (
                  <div
                    key={category}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '0.75rem',
                      border: '1px solid #e5e7eb',
                      borderRadius: '4px'
                    }}
                  >
                    <span style={{ fontWeight: 'bold', textTransform: 'capitalize' }}>{category}</span>
                    <span style={{ color: '#6b7280' }}>{count} document{count !== 1 ? 's' : ''}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
