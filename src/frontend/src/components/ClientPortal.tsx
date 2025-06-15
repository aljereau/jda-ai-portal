/**
 * Client Portal Component
 * Provides read-only access to proposals and project progress for client users.
 * 
 * Features:
 * - Client-specific proposal viewing
 * - Project progress visualization
 * - Read-only access controls
 * - Client-friendly interface design
 */

import React, { useState, useEffect } from 'react';

// Types
interface Proposal {
  id: number;
  project_name: string;
  client_name: string;
  phase: string;
  status: string;
  content: string;
  created_at: string;
  updated_at: string;
  share_token?: string;
}

interface ProjectStatus {
  proposal_id: number;
  project_name: string;
  client_name: string;
  current_phase: string;
  next_phase: string | null;
  progress_percentage: number;
  phases: {
    exploratory: { completed: boolean; is_current: boolean };
    discovery: { completed: boolean; is_current: boolean };
    development: { completed: boolean; is_current: boolean };
    deployment: { completed: boolean; is_current: boolean };
  };
  milestones: Array<{
    name: string;
    description: string;
  }>;
  timeline: {
    start_date: string | null;
    estimated_completion: string | null;
    actual_completion: string | null;
  };
}

interface ClientPortalProps {
  clientId?: number;
  shareToken?: string;
  isPublicAccess?: boolean;
}

const ClientPortal: React.FC<ClientPortalProps> = ({ 
  clientId, 
  shareToken, 
  isPublicAccess = false 
}) => {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [selectedProposal, setSelectedProposal] = useState<Proposal | null>(null);
  const [projectStatus, setProjectStatus] = useState<ProjectStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('proposals');

  // Fetch client proposals
  useEffect(() => {
    fetchClientProposals();
  }, [clientId, shareToken]);

  // Fetch project status when proposal is selected
  useEffect(() => {
    if (selectedProposal) {
      fetchProjectStatus(selectedProposal.id);
    }
  }, [selectedProposal]);

  const fetchClientProposals = async () => {
    try {
      setLoading(true);
      setError(null);

      let url = '/api/v1/proposals/';
      const params = new URLSearchParams();
      
      if (isPublicAccess && shareToken) {
        // Public access via share token
        url = `/api/v1/proposals/shared/${shareToken}`;
      } else {
        // Authenticated client access
        params.append('status', 'approved');
        params.append('status', 'sent');
        params.append('status', 'accepted');
        url += `?${params.toString()}`;
      }

      const response = await fetch(url, {
        headers: {
          'Authorization': isPublicAccess ? '' : `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch proposals: ${response.statusText}`);
      }

      const data = await response.json();
      const proposalList = Array.isArray(data) ? data : [data];
      setProposals(proposalList);
      
      // Auto-select first proposal if available
      if (proposalList.length > 0) {
        setSelectedProposal(proposalList[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load proposals');
    } finally {
      setLoading(false);
    }
  };

  const fetchProjectStatus = async (proposalId: number) => {
    try {
      const response = await fetch(`/api/v1/proposals/${proposalId}/project-status`, {
        headers: {
          'Authorization': isPublicAccess ? '' : `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch project status');
      }

      const status = await response.json();
      setProjectStatus(status);
    } catch (err) {
      console.error('Error fetching project status:', err);
      // Don't set error state for project status as it's secondary
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status.toLowerCase()) {
      case 'approved': return 'bg-green-100 text-green-800';
      case 'sent': return 'bg-blue-100 text-blue-800';
      case 'accepted': return 'bg-purple-100 text-purple-800';
      case 'in_review': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getPhaseColor = (phase: string): string => {
    switch (phase.toLowerCase()) {
      case 'exploratory': return 'bg-blue-100 text-blue-800';
      case 'discovery': return 'bg-yellow-100 text-yellow-800';
      case 'development': return 'bg-orange-100 text-orange-800';
      case 'deployment': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'Not set';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const handleExportProposal = async (proposalId: number, format: string) => {
    try {
      const response = await fetch(`/api/v1/proposals/${proposalId}/export/${format}`, {
        headers: {
          'Authorization': isPublicAccess ? '' : `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Export failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `proposal-${proposalId}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Export error:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your project information...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="max-w-md p-6 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (proposals.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <svg className="h-16 w-16 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Proposals Available</h2>
          <p className="text-gray-600">There are currently no proposals available for viewing.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Client Portal</h1>
              <p className="text-gray-600">View your project proposals and track progress</p>
            </div>
            {selectedProposal && (
              <div className="flex items-center space-x-2">
                <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                <span className="text-sm font-medium text-gray-900">
                  {selectedProposal.client_name}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar - Proposal List */}
          <div className="lg:col-span-1">
            <div className="bg-white shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">Your Proposals</h3>
                <div className="space-y-2">
                  {proposals.map((proposal) => (
                    <div
                      key={proposal.id}
                      className={`p-4 cursor-pointer border-l-4 transition-colors rounded-r-lg ${
                        selectedProposal?.id === proposal.id
                          ? 'bg-blue-50 border-blue-500'
                          : 'hover:bg-gray-50 border-transparent'
                      }`}
                      onClick={() => setSelectedProposal(proposal)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-medium text-gray-900 truncate">
                            {proposal.project_name}
                          </h3>
                          <div className="mt-1 flex items-center space-x-2">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(proposal.status)}`}>
                              {proposal.status.replace('_', ' ')}
                            </span>
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPhaseColor(proposal.phase)}`}>
                              {proposal.phase}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            Updated {formatDate(proposal.updated_at)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            {selectedProposal && (
              <div>
                {/* Tab Navigation */}
                <div className="border-b border-gray-200 mb-6">
                  <nav className="-mb-px flex space-x-8">
                    <button
                      onClick={() => setActiveTab('proposals')}
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${
                        activeTab === 'proposals'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      Proposal Details
                    </button>
                    <button
                      onClick={() => setActiveTab('progress')}
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${
                        activeTab === 'progress'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      Project Progress
                    </button>
                    <button
                      onClick={() => setActiveTab('timeline')}
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${
                        activeTab === 'timeline'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      Timeline
                    </button>
                  </nav>
                </div>

                {/* Proposal Details Tab */}
                {activeTab === 'proposals' && (
                  <div className="space-y-6">
                    <div className="bg-white shadow rounded-lg">
                      <div className="px-4 py-5 sm:p-6">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <h2 className="text-xl font-semibold text-gray-900">{selectedProposal.project_name}</h2>
                            <p className="text-gray-600 mt-1">
                              Created {formatDate(selectedProposal.created_at)}
                            </p>
                          </div>
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => handleExportProposal(selectedProposal.id, 'pdf')}
                              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                            >
                              <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                              Download PDF
                            </button>
                            <button
                              onClick={() => handleExportProposal(selectedProposal.id, 'html')}
                              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                            >
                              <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                              View HTML
                            </button>
                          </div>
                        </div>
                        <div className="prose max-w-none">
                          <div 
                            dangerouslySetInnerHTML={{ 
                              __html: selectedProposal.content || '<p>Proposal content is being prepared...</p>' 
                            }} 
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Project Progress Tab */}
                {activeTab === 'progress' && projectStatus && (
                  <div className="space-y-6">
                    {/* Progress Overview */}
                    <div className="bg-white shadow rounded-lg">
                      <div className="px-4 py-5 sm:p-6">
                        <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">Project Progress Overview</h3>
                        <div className="space-y-4">
                          <div>
                            <div className="flex justify-between text-sm mb-2">
                              <span>Overall Progress</span>
                              <span>{Math.round(projectStatus.progress_percentage)}%</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div 
                                className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                                style={{ width: `${projectStatus.progress_percentage}%` }}
                              ></div>
                            </div>
                          </div>
                          
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {Object.entries(projectStatus.phases).map(([phase, info]) => {
                              const phaseInfo = info as { completed: boolean; is_current: boolean };
                              return (
                                <div key={phase} className="text-center">
                                  <div className={`w-12 h-12 rounded-full mx-auto mb-2 flex items-center justify-center ${
                                    phaseInfo.completed 
                                      ? 'bg-green-100 text-green-600' 
                                      : phaseInfo.is_current 
                                        ? 'bg-blue-100 text-blue-600' 
                                        : 'bg-gray-100 text-gray-400'
                                  }`}>
                                    {phaseInfo.completed ? (
                                      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                      </svg>
                                    ) : phaseInfo.is_current ? (
                                      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                      </svg>
                                    ) : (
                                      <div className="w-3 h-3 rounded-full bg-current" />
                                    )}
                                  </div>
                                  <p className="text-xs font-medium capitalize">{phase}</p>
                                  <p className="text-xs text-gray-500">
                                    {phaseInfo.completed ? 'Complete' : phaseInfo.is_current ? 'Current' : 'Pending'}
                                  </p>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Current Phase Milestones */}
                    <div className="bg-white shadow rounded-lg">
                      <div className="px-4 py-5 sm:p-6">
                        <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                          Current Phase: {projectStatus.current_phase}
                        </h3>
                        <div className="space-y-3">
                          {projectStatus.milestones.map((milestone, index) => (
                            <div key={index} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                              <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                                <span className="text-xs font-medium">{index + 1}</span>
                              </div>
                              <div>
                                <h4 className="text-sm font-medium text-gray-900">{milestone.name}</h4>
                                <p className="text-sm text-gray-600">{milestone.description}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Timeline Tab */}
                {activeTab === 'timeline' && projectStatus && (
                  <div className="space-y-6">
                    <div className="bg-white shadow rounded-lg">
                      <div className="px-4 py-5 sm:p-6">
                        <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">Project Timeline</h3>
                        <div className="space-y-4">
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="text-center p-4 bg-blue-50 rounded-lg">
                              <svg className="h-8 w-8 text-blue-600 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                              </svg>
                              <h3 className="font-medium text-gray-900">Start Date</h3>
                              <p className="text-sm text-gray-600">
                                {formatDate(projectStatus.timeline.start_date)}
                              </p>
                            </div>
                            <div className="text-center p-4 bg-yellow-50 rounded-lg">
                              <svg className="h-8 w-8 text-yellow-600 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              <h3 className="font-medium text-gray-900">Estimated Completion</h3>
                              <p className="text-sm text-gray-600">
                                {formatDate(projectStatus.timeline.estimated_completion)}
                              </p>
                            </div>
                            <div className="text-center p-4 bg-green-50 rounded-lg">
                              <svg className="h-8 w-8 text-green-600 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              <h3 className="font-medium text-gray-900">Actual Completion</h3>
                              <p className="text-sm text-gray-600">
                                {formatDate(projectStatus.timeline.actual_completion)}
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClientPortal; 