/**
 * ProposalEditor Component
 * Provides interface for reviewing and editing proposals with real-time preview
 */

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Box, 
  Grid, 
  Paper, 
  Typography, 
  Button, 
  TextField, 
  Select, 
  MenuItem, 
  FormControl, 
  InputLabel,
  Chip,
  Alert,
  CircularProgress,
  Divider,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Edit as EditIcon,
  Preview as PreviewIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  Remove as RemoveIcon,
  Download as DownloadIcon
} from '@mui/icons-material';

import { useAuth } from '../hooks/useAuth';
import { proposalService } from '../services/proposalService';
import { Proposal, ProposalStatus, ProjectPhase } from '../types/proposal';

interface ProposalEditorProps {
  proposalId: number;
  onSave?: (proposal: Proposal) => void;
  onStatusChange?: (status: ProposalStatus) => void;
}

interface EditableSection {
  id: string;
  title: string;
  content: string;
  editable: boolean;
  aiGenerated: boolean;
}

export const ProposalEditor: React.FC<ProposalEditorProps> = ({
  proposalId,
  onSave,
  onStatusChange
}) => {
  const { user } = useAuth();
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);
  const [renderedHtml, setRenderedHtml] = useState<string>('');
  
  // Editable sections state
  const [sections, setSections] = useState<EditableSection[]>([]);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);

  // Load proposal data
  const loadProposal = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await proposalService.getProposal(proposalId);
      setProposal(data);
      
      // Parse content into editable sections
      if (data.content) {
        const parsedSections = parseContentIntoSections(data.content);
        setSections(parsedSections);
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load proposal');
    } finally {
      setLoading(false);
    }
  }, [proposalId]);

  // Load rendered preview
  const loadPreview = useCallback(async () => {
    try {
      const response = await proposalService.renderTemplate(proposalId);
      setRenderedHtml(response.rendered_html);
    } catch (err) {
      console.error('Failed to load preview:', err);
    }
  }, [proposalId]);

  useEffect(() => {
    loadProposal();
  }, [loadProposal]);

  useEffect(() => {
    if (previewMode) {
      loadPreview();
    }
  }, [previewMode, loadPreview]);

  // Parse HTML content into editable sections
  const parseContentIntoSections = (content: string): EditableSection[] => {
    const sections: EditableSection[] = [];
    
    // Basic parsing - in production, use a proper HTML parser
    const sectionRegex = /<section[^>]*class="([^"]*)"[^>]*>(.*?)<\/section>/gs;
    let match;
    let index = 0;
    
    while ((match = sectionRegex.exec(content)) !== null) {
      const className = match[1];
      const sectionContent = match[2];
      
      sections.push({
        id: `section-${index}`,
        title: extractSectionTitle(sectionContent),
        content: sectionContent,
        editable: !className.includes('header') && !className.includes('footer'),
        aiGenerated: className.includes('ai-generated')
      });
      
      index++;
    }
    
    return sections.length > 0 ? sections : [
      {
        id: 'main-content',
        title: 'Main Content',
        content: content,
        editable: true,
        aiGenerated: false
      }
    ];
  };

  // Extract section title from HTML content
  const extractSectionTitle = (content: string): string => {
    const titleMatch = content.match(/<h[1-6][^>]*>(.*?)<\/h[1-6]>/);
    if (titleMatch) {
      return titleMatch[1].replace(/<[^>]*>/g, ''); // Strip HTML tags
    }
    return 'Untitled Section';
  };

  // Save proposal changes
  const handleSave = async () => {
    if (!proposal) return;
    
    try {
      setSaving(true);
      setError(null);
      
      // Reconstruct content from sections
      const updatedContent = sections.map(section => 
        `<section class="section ${section.aiGenerated ? 'ai-generated' : ''}">${section.content}</section>`
      ).join('\n');
      
      const updatedProposal = await proposalService.updateProposal(proposalId, {
        content: updatedContent
      });
      
      setProposal(updatedProposal);
      setEditMode(false);
      
      if (onSave) {
        onSave(updatedProposal);
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save proposal');
    } finally {
      setSaving(false);
    }
  };

  // Update proposal status
  const handleStatusChange = async (newStatus: ProposalStatus) => {
    if (!proposal) return;
    
    try {
      const updatedProposal = await proposalService.updateProposal(proposalId, {
        status: newStatus
      });
      
      setProposal(updatedProposal);
      
      if (onStatusChange) {
        onStatusChange(newStatus);
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status');
    }
  };

  // Update section content
  const updateSectionContent = (sectionId: string, newContent: string) => {
    setSections(prev => prev.map(section => 
      section.id === sectionId 
        ? { ...section, content: newContent }
        : section
    ));
  };

  // Add new section
  const addSection = () => {
    const newSection: EditableSection = {
      id: `section-${Date.now()}`,
      title: 'New Section',
      content: '<h3>New Section</h3><p>Add your content here...</p>',
      editable: true,
      aiGenerated: false
    };
    
    setSections(prev => [...prev, newSection]);
    setSelectedSection(newSection.id);
  };

  // Remove section
  const removeSection = (sectionId: string) => {
    setSections(prev => prev.filter(section => section.id !== sectionId));
    if (selectedSection === sectionId) {
      setSelectedSection(null);
    }
  };

  // Re-extract requirements from transcript
  const handleReExtractRequirements = async () => {
    try {
      setLoading(true);
      await proposalService.extractRequirements(proposalId);
      await loadProposal(); // Reload to get updated data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to re-extract requirements');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!proposal) {
    return (
      <Alert severity="error">
        Proposal not found or you don't have permission to view it.
      </Alert>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <Typography variant="h4" gutterBottom>
              {proposal.project_name}
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              Client: {proposal.client_name} | Phase: {proposal.phase}
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Box display="flex" gap={1} justifyContent="flex-end" flexWrap="wrap">
              <Chip 
                label={proposal.status} 
                color={getStatusColor(proposal.status)}
                variant="outlined"
              />
              
              {user?.role !== 'client' && (
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>Status</InputLabel>
                  <Select
                    value={proposal.status}
                    label="Status"
                    onChange={(e) => handleStatusChange(e.target.value as ProposalStatus)}
                  >
                    <MenuItem value="draft">Draft</MenuItem>
                    <MenuItem value="in_review">In Review</MenuItem>
                    <MenuItem value="approved">Approved</MenuItem>
                    <MenuItem value="sent">Sent</MenuItem>
                  </Select>
                </FormControl>
              )}
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Action Bar */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" gap={1} alignItems="center" flexWrap="wrap">
          <Button
            variant={editMode ? "contained" : "outlined"}
            startIcon={<EditIcon />}
            onClick={() => setEditMode(!editMode)}
            disabled={user?.role === 'client'}
          >
            {editMode ? 'Exit Edit' : 'Edit'}
          </Button>
          
          <Button
            variant={previewMode ? "contained" : "outlined"}
            startIcon={<PreviewIcon />}
            onClick={() => setPreviewMode(!previewMode)}
          >
            Preview
          </Button>
          
          {editMode && (
            <>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleSave}
                disabled={saving}
                color="primary"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
              
              <Button
                startIcon={<AddIcon />}
                onClick={addSection}
                variant="outlined"
              >
                Add Section
              </Button>
            </>
          )}
          
          {user?.role !== 'client' && (
            <Button
              startIcon={<RefreshIcon />}
              onClick={handleReExtractRequirements}
              variant="outlined"
            >
              Re-extract Requirements
            </Button>
          )}
          
          <Button
            startIcon={<DownloadIcon />}
            onClick={() => window.open(`/api/v1/proposals/${proposalId}/export`, '_blank')}
            variant="outlined"
          >
            Export
          </Button>
        </Box>
      </Paper>

      {/* Main Content */}
      <Grid container spacing={3}>
        {/* Section List (Edit Mode) */}
        {editMode && (
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Sections
              </Typography>
              
              {sections.map((section) => (
                <Box
                  key={section.id}
                  sx={{
                    p: 1,
                    mb: 1,
                    border: 1,
                    borderColor: selectedSection === section.id ? 'primary.main' : 'grey.300',
                    borderRadius: 1,
                    cursor: 'pointer',
                    bgcolor: selectedSection === section.id ? 'primary.50' : 'transparent'
                  }}
                  onClick={() => setSelectedSection(section.id)}
                >
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2">
                      {section.title}
                      {section.aiGenerated && (
                        <Chip size="small" label="AI" sx={{ ml: 1 }} />
                      )}
                    </Typography>
                    
                    {section.editable && (
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          removeSection(section.id);
                        }}
                      >
                        <RemoveIcon />
                      </IconButton>
                    )}
                  </Box>
                </Box>
              ))}
            </Paper>
          </Grid>
        )}

        {/* Content Editor/Viewer */}
        <Grid item xs={12} md={editMode ? 8 : 12}>
          <Paper sx={{ p: 3, minHeight: '600px' }}>
            {previewMode ? (
              // Preview Mode
              <Box>
                <Typography variant="h6" gutterBottom>
                  Preview
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Box
                  dangerouslySetInnerHTML={{ __html: renderedHtml }}
                  sx={{
                    '& img': { maxWidth: '100%' },
                    '& table': { width: '100%', borderCollapse: 'collapse' },
                    '& th, & td': { border: 1, borderColor: 'grey.300', p: 1 }
                  }}
                />
              </Box>
            ) : editMode && selectedSection ? (
              // Edit Mode
              <Box>
                <Typography variant="h6" gutterBottom>
                  Edit Section: {sections.find(s => s.id === selectedSection)?.title}
                </Typography>
                <Divider sx={{ mb: 2 }} />
                
                <TextField
                  fullWidth
                  multiline
                  rows={20}
                  value={sections.find(s => s.id === selectedSection)?.content || ''}
                  onChange={(e) => updateSectionContent(selectedSection, e.target.value)}
                  variant="outlined"
                  placeholder="Enter section content (HTML supported)..."
                />
              </Box>
            ) : (
              // View Mode
              <Box>
                <Typography variant="h6" gutterBottom>
                  Proposal Content
                </Typography>
                <Divider sx={{ mb: 2 }} />
                
                {sections.map((section) => (
                  <Box key={section.id} sx={{ mb: 3 }}>
                    <Box
                      dangerouslySetInnerHTML={{ __html: section.content }}
                      sx={{
                        '& h1, & h2, & h3, & h4, & h5, & h6': { 
                          color: 'primary.main',
                          mb: 1
                        },
                        '& p': { mb: 2 },
                        '& ul, & ol': { mb: 2, pl: 3 }
                      }}
                    />
                    {section.aiGenerated && (
                      <Chip size="small" label="AI Generated" color="info" />
                    )}
                  </Box>
                ))}
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

// Helper function to get status color
const getStatusColor = (status: ProposalStatus): "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning" => {
  switch (status) {
    case 'draft': return 'default';
    case 'in_review': return 'warning';
    case 'approved': return 'success';
    case 'sent': return 'info';
    case 'accepted': return 'success';
    case 'rejected': return 'error';
    default: return 'default';
  }
};

export default ProposalEditor; 