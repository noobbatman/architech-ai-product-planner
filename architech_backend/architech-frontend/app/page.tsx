'use client'; 

import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

// --- TYPE DEFINITIONS ---
interface ProjectStatus {
  project_id: string;
  status: 'PENDING' | 'BLUEPRINTING' | 'SIMULATING' | 'COMPLETE' | 'FAILED';
  message: string;
  trello_board_url: string | null;
  frontend_summary: string | null;
}

interface ProjectListItem {
  project_id: string;
  initial_idea: string;
  status: 'PENDING' | 'BLUEPRINTING' | 'SIMULATING' | 'COMPLETE' | 'FAILED';
  trello_board_url: string | null;
  created_at: string;
  frontend_summary: string | null;
}

// --- STYLES ---
// We define our styles as JavaScript objects
const styles = {
  header: {
    fontSize: '3.75rem',
    fontWeight: '700',
    textAlign: 'center',
    lineHeight: 1.2,
  } as React.CSSProperties,
  headerSpan: {
    color: '#3b82f6', // Blue color
  },
  subtitle: {
    fontSize: '1.25rem',
    color: '#9ca3af', // Gray color
    textAlign: 'center',
    marginTop: '1rem',
    marginBottom: '3rem',
  },
  textarea: (isLoading: boolean): React.CSSProperties => ({
    width: '100%',
    padding: '1rem',
    fontSize: '1rem',
    color: '#ffffff',
    backgroundColor: '#1f2937', // Darker gray
    border: '1px solid #374151',
    borderRadius: '0.5rem',
    boxShadow: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
    outline: 'none',
    opacity: isLoading ? 0.7 : 1,
  }),
  button: (isLoading: boolean, hasIdea: boolean): React.CSSProperties => ({
    width: '100%',
    marginTop: '1rem',
    padding: '1rem',
    fontSize: '1.125rem',
    fontWeight: '700',
    color: '#ffffff',
    backgroundColor: isLoading || !hasIdea ? '#4b5563' : '#2563eb',
    borderRadius: '0.5rem',
    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    cursor: isLoading || !hasIdea ? 'not-allowed' : 'pointer',
    border: 'none',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    opacity: isLoading || !hasIdea ? 0.6 : 1,
  }),
  // ... (Other styles defined below)
};


// --- COMPONENTS ---
function Spinner() {
  return <div className="spinner"></div>; // Uses the class from globals.css
}

function ProjectCard({ project }: { project: ProjectListItem }) {
  const getStatusColor = () => {
    switch (project.status) {
      case 'COMPLETE': return '#22c55e'; // Green
      case 'FAILED': return '#ef4444'; // Red
      default: return '#eab308'; // Yellow
    }
  };

  const cardStyle: React.CSSProperties = {
    padding: '1rem',
    backgroundColor: '#1f2937', // Dark gray
    borderRadius: '0.5rem',
    borderLeft: `4px solid ${getStatusColor()}`,
    boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  };

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
          {new Date(project.created_at).toLocaleString()}
        </p>
        <span style={{
          padding: '0.25rem 0.75rem',
          fontSize: '0.75rem',
          fontWeight: '700',
          borderRadius: '9999px',
          color: '#f0fdf4',
          backgroundColor: project.status === 'COMPLETE' ? '#166534' : project.status === 'FAILED' ? '#991b1b' : '#a16207',
        }}>
          {project.status}
        </span>
      </div>
      <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginTop: '0.5rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {project.initial_idea}
      </h3>
      
      {project.status === 'COMPLETE' && project.frontend_summary && (
        <div className="markdown-summary" style={{ marginTop: '0.5rem', color: '#d1d5db', fontSize: '0.875rem', lineHeight: '1.625' }}>
          <ReactMarkdown>
            {project.frontend_summary}
          </ReactMarkdown>
        </div>
      )}

      {project.status === 'COMPLETE' && project.trello_board_url && (
        <a
          href={project.trello_board_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: '#60a5fa', textDecoration: 'underline', marginTop: '0.5rem', display: 'inline-block', fontWeight: '500', fontSize: '0.875rem' }}
        >
          View Full Technical Plan (Trello)
        </a>
      )}
    </div>
  );
}

// --- MAIN PAGE ---
export default function HomePage() {
  const [idea, setIdea] = useState('');
  const [pollingId, setPollingId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [finalResult, setFinalResult] = useState<ProjectStatus | null>(null);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [isListLoading, setIsListLoading] = useState(true);
  const [submittedIdea, setSubmittedIdea] = useState('');

  const API_URL = 'http://127.0.0.1:8000';

  const fetchProjects = async () => {
    setIsListLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/projects`);
      if (!response.ok) {
        throw new Error('Failed to fetch project history');
      }
      const data: ProjectListItem[] = await response.json();
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    }
    setIsListLoading(false);
  };

  useEffect(() => {
    fetchProjects(); 
    
    if (!pollingId || !isLoading) return;

    const intervalId = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/projects/${pollingId}/status`);
        if (!response.ok) throw new Error('Failed to get project status');

        const data: ProjectStatus = await response.json();
        setStatusMessage(data.message);

        if (data.status === 'COMPLETE' || data.status === 'FAILED') {
          setIsLoading(false);
          setPollingId(null);
          clearInterval(intervalId);
          setSubmittedIdea(''); 
          
          if (data.status === 'COMPLETE') {
            setFinalResult(data);
          } else {
            setError(data.message || 'The job failed.');
          }

          // Manually add the new project to the list state
          setProjects(prevProjects => [
            {
              project_id: data.project_id,
              initial_idea: submittedIdea,
              status: data.status,
              trello_board_url: data.trello_board_url,
              created_at: new Date().toISOString(),
              frontend_summary: data.frontend_summary,
            } as ProjectListItem,
            ...prevProjects.filter(p => p.project_id !== data.project_id)
          ]);
        }
      } catch (err) {
        setIsLoading(false);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
        setPollingId(null);
        clearInterval(intervalId);
      }
    }, 3000);

    return () => clearInterval(intervalId);
  }, [pollingId, isLoading, submittedIdea]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading || !idea) return;

    setIsLoading(true);
    setError(null);
    setFinalResult(null);
    setSubmittedIdea(idea); 
    setStatusMessage('Submitting your idea...');

    try {
      const response = await fetch(`${API_URL}/api/v1/projects/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initial_idea: idea }),
      });

      if (response.status !== 202) { 
        const errorData = await response.json();
        throw new Error(errorData.detail || `API Error: ${response.statusText}`);
      }

      const data: ProjectStatus = await response.json();
      setPollingId(data.project_id);
      setStatusMessage(data.message);
      setIdea(''); 
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      setIsLoading(false);
    }
  };

  // --- RENDER ---
  return (
    <main>
      <div className="container">
        
        {/* Header */}
        <h1 style={styles.header}>
          Archi<span style={styles.headerSpan}>TECH</span>
        </h1>
        <p style={styles.subtitle}>
          Input the core idea. Receive the executive summary and developer backlog.
        </p>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ width: '100%' }}>
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="e.g., An app that helps people find local dog walkers..."
            style={styles.textarea(isLoading)}
            rows={5}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !idea}
            style={styles.button(isLoading, !!idea)}
          >
            {isLoading ? (
              <>
                <Spinner />
                {statusMessage || 'Generating Plan...'}
              </>
            ) : (
              'Build My Blueprint'
            )}
          </button>
        </form>

        {/* --- Output Area (New Results) --- */}
        <div style={{ marginTop: '2rem' }}>
          {error && (
            <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#7f1d1d', border: '1px solid #991b1b', color: '#fecaca', borderRadius: '0.5rem' }}>
              <h3 style={{ fontWeight: '700' }}>Error</h3>
              <p>{error}</p>
            </div>
          )}

          {finalResult && (
            <div style={{ marginTop: '2rem', padding: '1.5rem', backgroundColor: '#14532d', border: '1px solid #166534', color: '#dcfce7', borderRadius: '0.5rem' }}>
              <h3 style={{ fontSize: '1.5rem', fontWeight: '700' }}>✅ Generation Complete</h3>
              
              <h4 style={{ marginTop: '1rem', fontSize: '1.125rem', fontWeight: '600', color: 'white' }}>Executive Summary:</h4>
              <div className="markdown-summary" style={{ marginTop: '0.5rem', lineHeight: '1.625', fontStyle: 'italic' }}>
                <ReactMarkdown>
                  {finalResult.frontend_summary || "Summary not available for this project."}
                </ReactMarkdown>
              </div>

              <a
                href={finalResult.trello_board_url!}
                target="_blank"
                rel="noopener noreferrer"
                style={{ marginTop: '1.5rem', display: 'inline-block', padding: '0.75rem 1.5rem', backgroundColor: 'white', color: '#14532d', fontWeight: '700', borderRadius: '0.5rem', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', textDecoration: 'none' }}
              >
                View Full Technical Backlog (Trello)
              </a>
            </div>
          )}
        </div>

        {/* --- Project History --- */}
        <div style={{ marginTop: '6rem', width: '100%' }}>
          <h2 style={{ fontSize: '1.875rem', fontWeight: '700', color: 'white', marginBottom: '1.5rem' }}>Project History</h2>
          {isListLoading && <p style={{ color: '#9ca3af' }}>Loading projects...</p>}
          
          {!isListLoading && projects.length === 0 && (
            <p style={{ color: '#9ca3af' }}>No projects found. Generate one to see it here!</p>
          )}

          {!isListLoading && projects.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {projects.map((project) => (
                <ProjectCard key={project.project_id} project={project} />
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}