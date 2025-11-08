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

// --- COMPONENTS ---
function Spinner() {
  return (
    <svg
      className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
  );
}

function ProjectCard({ project }: { project: ProjectListItem }) {
  const getStatusColor = () => {
    switch (project.status) {
      case 'COMPLETE':
        return 'border-green-500';
      case 'FAILED':
        return 'border-red-500';
      default:
        return 'border-yellow-500';
    }
  };

  return (
    <div className={`p-4 bg-gray-800 rounded-lg border-l-4 ${getStatusColor()} shadow-md`}>
      <div className="flex justify-between items-center">
        <p className="text-sm text-gray-400">
          {new Date(project.created_at).toLocaleString()}
        </p>
        <span className={`px-3 py-1 text-xs font-bold rounded-full ${
          project.status === 'COMPLETE' ? 'bg-green-700 text-green-100' :
          project.status === 'FAILED' ? 'bg-red-700 text-red-100' :
          'bg-yellow-700 text-yellow-100 animate-pulse'
        }`}>
          {project.status}
        </span>
      </div>
      <h3 className="text-lg font-semibold mt-2 truncate">{project.initial_idea}</h3>
      
      {/* Display the non-technical summary here */}
      {project.status === 'COMPLETE' && project.frontend_summary && (
      <div className="markdown-summary mt-2 text-gray-300 text-sm leading-relaxed">
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
          className="text-blue-400 hover:underline mt-2 inline-block font-medium text-sm"
        >
          View Full Technical Plan (Trello)
        </a>
      )}
    </div>
  );
}


// --- MAIN PAGE ---
export default function HomePage() {
  // --- State Management ---
  const [idea, setIdea] = useState('');
  const [pollingId, setPollingId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [finalResult, setFinalResult] = useState<ProjectStatus | null>(null);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [isListLoading, setIsListLoading] = useState(true);
  const [submittedIdea, setSubmittedIdea] = useState('');

  // API endpoint is local on Windows
  const API_URL = 'http://127.0.0.1:8000';

  // --- DATA FETCHING ---
  const fetchProjects = async () => {
    setIsListLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/projects`); // Correct endpoint without slash
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

  // Initial load and Polling Effect
  useEffect(() => {
    fetchProjects(); 
    
    if (!pollingId || !isLoading) return;

    const intervalId = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/projects/${pollingId}/status`);
        if (!response.ok) throw new Error('Failed to get project status');

        const data: ProjectStatus = await response.json();
        setStatusMessage(data.message);

        if (data.status === 'COMPLETE') {
          setIsLoading(false);
          setFinalResult(data);
          setPollingId(null);
          clearInterval(intervalId);
          
          // --- FIX: Use a unique key helper and filter for duplicates ---
          setProjects(prevProjects => {
              const newProject: ProjectListItem = {
                  project_id: data.project_id,
                  initial_idea: submittedIdea,
                  status: 'COMPLETE',
                  trello_board_url: data.trello_board_url,
                  created_at: new Date().toISOString(),
                  frontend_summary: data.frontend_summary,
              } as ProjectListItem;

              // Filter out the current project if it already exists in the list
              const filteredProjects = prevProjects.filter(p => p.project_id !== data.project_id);
              
              // Return the new project at the top
              return [newProject, ...filteredProjects];
          });
          setSubmittedIdea('');
          
        } else if (data.status === 'FAILED') {
          setIsLoading(false);
          setError(data.message || 'The job failed.');
          setPollingId(null);
          clearInterval(intervalId);
          
          // FIX 2: Manually add failed project to state
          setProjects(prevProjects => [
            {
              project_id: data.project_id,
              initial_idea: submittedIdea,
              status: 'FAILED',
              trello_board_url: null,
              created_at: new Date().toISOString(),
              frontend_summary: data.frontend_summary,
            } as ProjectListItem,
            ...prevProjects
          ]);
          setSubmittedIdea(''); 
        }
        
      } catch (err) {
        setIsLoading(false);
        setError(err instanceof Error ? err.message : 'An unknown error occurred during polling');
        setPollingId(null);
        clearInterval(intervalId);
      }
    }, 3000);

    return () => clearInterval(intervalId);

  }, [pollingId, isLoading, submittedIdea]);

  // --- Form Submission Handler ---
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
      setError(err instanceof Error ? err.message : 'An unknown error occurred during submission');
      setIsLoading(false);
    }
  };

  // --- RENDER ---
  return (
    <main className="flex min-h-screen flex-col items-center p-12 md:p-24 bg-gray-900">
      <div className="w-full max-w-3xl">
        
        {/* Header */}
        <h1 className="text-5xl md:text-6xl font-bold text-center">
          Archi<span className="text-blue-500">TECH</span>
        </h1>
        <p className="text-lg md:text-xl text-gray-400 text-center mt-4 mb-12">
          Input the core idea. Receive the executive summary and developer backlog.
        </p>

        {/* Form */}
        <form onSubmit={handleSubmit} className="w-full">
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="e.g., An app that helps people find local dog walkers..."
            className="w-full p-4 text-md text-white bg-gray-800 border border-gray-700 rounded-lg shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            rows={5}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !idea}
            className="w-full mt-4 p-4 text-lg font-bold bg-blue-600 rounded-lg shadow-lg hover:bg-blue-700 transition-all disabled:bg-gray-700 disabled:text-gray-400 disabled:cursor-not-allowed flex items-center justify-center"
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
        <div className="mt-8">
          {error && (
            <div className="mt-8 p-4 bg-red-900 border border-red-700 text-red-100 rounded-lg w-full">
              <h3 className="font-bold">Error</h3>
              <p>{error}</p>
            </div>
          )}

          {finalResult && (
  <div className="mt-8 p-6 bg-green-900 border border-green-700 text-green-100 rounded-lg w-full shadow-xl">
    <h3 className="text-2xl font-bold">✅ Generation Complete</h3>

    <div className="markdown-summary mt-2 text-md leading-relaxed italic">
      <ReactMarkdown>
        {finalResult.frontend_summary || "Summary not available for this project."}
      </ReactMarkdown>
    </div>

    <a
      href={finalResult.trello_board_url!}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-6 inline-block px-6 py-3 bg-white text-green-900 font-bold rounded-lg shadow-lg hover:opacity-90 transition-all"
              >
                View Full Technical Backlog (Trello)
              </a>
            </div>
          )}
        </div>

        {/* --- Project History --- */}
        <div className="mt-24 w-full">
          <h2 className="text-3xl font-bold text-white mb-6">Project History</h2>
          {isListLoading && <p className="text-gray-400">Loading projects...</p>}
          
          {!isListLoading && projects.length === 0 && (
            <p className="text-gray-400">No projects found. Generate one to see it here!</p>
          )}

          {!isListLoading && projects.length > 0 && (
            <div className="flex flex-col gap-4">
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