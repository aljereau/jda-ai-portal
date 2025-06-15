import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  Menu,
  ListItemIcon,
  ListItemText,
  Tooltip,
  Badge,
  Autocomplete,
  DatePicker,
  Pagination
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Compare as CompareIcon,
  Analytics as AnalyticsIcon,
  Template as TemplateIcon,
  Workflow as WorkflowIcon,
  Download as DownloadIcon,
  ExpandMore as ExpandMoreIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Share as ShareIcon,
  FileCopy as CopyIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Sort as SortIcon,
  Clear as ClearIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { DatePicker as MuiDatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

// Types
interface ProposalSummary {
  id: string;
  title: string;
  status: string;
  phase: string;
  created_at: string;
  updated_at: string;
  creator_name: string;
  client_name?: string;
  assigned_to?: string;
  tags?: string[];
  priority?: 'low' | 'medium' | 'high';
  estimated_value?: number;
  completion_percentage?: number;
}

interface SearchFilters {
  text_search: string;
  status_filter: string[];
  phase_filter: string[];
  client_filter: string[];
  date_from?: Date;
  date_to?: Date;
  assigned_user: string[];
  tags: string[];
  priority: string[];
  sort_by: string;
  sort_order: 'asc' | 'desc';
}

interface ComparisonData {
  proposals: ProposalSummary[];
  comparison_metrics: {
    [key: string]: any;
  };
}

const ProposalDatabaseInterface: React.FC = () => {
  // State management
  const [activeTab, setActiveTab] = useState(0);
  const [proposals, setProposals] = useState<ProposalSummary[]>([]);
  const [filteredProposals, setFilteredProposals] = useState<ProposalSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Search and filter states
  const [searchFilters, setSearchFilters] = useState<SearchFilters>({
    text_search: '',
    status_filter: [],
    phase_filter: [],
    client_filter: [],
    assigned_user: [],
    tags: [],
    priority: [],
    sort_by: 'updated_at',
    sort_order: 'desc'
  });
  
  // Dialog states
  const [filterDialogOpen, setFilterDialogOpen] = useState(false);
  const [comparisonDialogOpen, setComparisonDialogOpen] = useState(false);
  const [analyticsDialogOpen, setAnalyticsDialogOpen] = useState(false);
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  
  // Selection and comparison
  const [selectedProposals, setSelectedProposals] = useState<string[]>([]);
  const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null);
  const [favoriteProposals, setFavoriteProposals] = useState<string[]>([]);
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(25);
  const [totalItems, setTotalItems] = useState(0);
  
  // Menu states
  const [sortMenuAnchor, setSortMenuAnchor] = useState<null | HTMLElement>(null);
  const [exportMenuAnchor, setExportMenuAnchor] = useState<null | HTMLElement>(null);

  // Available filter options (would typically come from API)
  const statusOptions = ['draft', 'in_review', 'approved', 'rejected', 'completed'];
  const phaseOptions = ['exploratory', 'discovery', 'development', 'deployment'];
  const clientOptions = ['Client A', 'Client B', 'Client C', 'Client D'];
  const userOptions = ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown'];
  const tagOptions = ['urgent', 'high-value', 'complex', 'simple', 'recurring'];
  const priorityOptions = ['low', 'medium', 'high'];

  // Load proposals on component mount and filter changes
  useEffect(() => {
    loadProposals();
  }, [searchFilters, currentPage]);

  // Apply client-side filtering
  useEffect(() => {
    applyFilters();
  }, [proposals, searchFilters]);

  const loadProposals = async (): Promise<void> => {
    try {
      setLoading(true);
      
      // Build query parameters
      const params = new URLSearchParams();
      if (searchFilters.text_search) params.append('search', searchFilters.text_search);
      if (searchFilters.status_filter.length > 0) params.append('status', searchFilters.status_filter.join(','));
      if (searchFilters.phase_filter.length > 0) params.append('phase', searchFilters.phase_filter.join(','));
      if (searchFilters.date_from) params.append('date_from', searchFilters.date_from.toISOString().split('T')[0]);
      if (searchFilters.date_to) params.append('date_to', searchFilters.date_to.toISOString().split('T')[0]);
      params.append('sort_by', searchFilters.sort_by);
      params.append('sort_order', searchFilters.sort_order);
      params.append('limit', itemsPerPage.toString());
      params.append('offset', ((currentPage - 1) * itemsPerPage).toString());
      
      const response = await fetch(`/api/v1/team-dashboard/proposals?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to load proposals');
      }
      
      const data = await response.json();
      setProposals(data);
      setTotalItems(data.length); // In real implementation, this would come from response headers
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load proposals');
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = (): void => {
    let filtered = [...proposals];
    
    // Apply client-side filters that weren't handled by the API
    if (searchFilters.client_filter.length > 0) {
      filtered = filtered.filter(p => 
        searchFilters.client_filter.includes(p.client_name || '')
      );
    }
    
    if (searchFilters.assigned_user.length > 0) {
      filtered = filtered.filter(p => 
        searchFilters.assigned_user.includes(p.assigned_to || '')
      );
    }
    
    if (searchFilters.tags.length > 0) {
      filtered = filtered.filter(p => 
        p.tags?.some(tag => searchFilters.tags.includes(tag))
      );
    }
    
    if (searchFilters.priority.length > 0) {
      filtered = filtered.filter(p => 
        searchFilters.priority.includes(p.priority || '')
      );
    }
    
    setFilteredProposals(filtered);
  };

  const handleSearch = useCallback((searchTerm: string) => {
    setSearchFilters(prev => ({
      ...prev,
      text_search: searchTerm
    }));
    setCurrentPage(1);
  }, []);

  const handleFilterChange = (filterKey: keyof SearchFilters, value: any): void => {
    setSearchFilters(prev => ({
      ...prev,
      [filterKey]: value
    }));
    setCurrentPage(1);
  };

  const clearFilters = (): void => {
    setSearchFilters({
      text_search: '',
      status_filter: [],
      phase_filter: [],
      client_filter: [],
      assigned_user: [],
      tags: [],
      priority: [],
      sort_by: 'updated_at',
      sort_order: 'desc'
    });
    setCurrentPage(1);
  };

  const handleProposalSelection = (proposalId: string, selected: boolean): void => {
    if (selected) {
      setSelectedProposals(prev => [...prev, proposalId]);
    } else {
      setSelectedProposals(prev => prev.filter(id => id !== proposalId));
    }
  };

  const handleSelectAll = (selected: boolean): void => {
    if (selected) {
      setSelectedProposals(filteredProposals.map(p => p.id));
    } else {
      setSelectedProposals([]);
    }
  };

  const toggleFavorite = (proposalId: string): void => {
    setFavoriteProposals(prev => 
      prev.includes(proposalId)
        ? prev.filter(id => id !== proposalId)
        : [...prev, proposalId]
    );
  };

  const handleCompareProposals = async (): Promise<void> => {
    if (selectedProposals.length < 2) {
      setError('Please select at least 2 proposals to compare');
      return;
    }
    
    try {
      setLoading(true);
      
      // In a real implementation, this would call a comparison API
      const selectedData = filteredProposals.filter(p => selectedProposals.includes(p.id));
      setComparisonData({
        proposals: selectedData,
        comparison_metrics: {
          // Mock comparison data
          average_completion_time: selectedData.reduce((acc, p) => acc + (p.completion_percentage || 0), 0) / selectedData.length,
          total_estimated_value: selectedData.reduce((acc, p) => acc + (p.estimated_value || 0), 0),
          status_distribution: selectedData.reduce((acc, p) => {
            acc[p.status] = (acc[p.status] || 0) + 1;
            return acc;
          }, {} as Record<string, number>)
        }
      });
      
      setComparisonDialogOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compare proposals');
    } finally {
      setLoading(false);
    }
  };

  const handleBulkExport = async (format: string): Promise<void> => {
    try {
      setLoading(true);
      
      const exportData = {
        proposal_ids: selectedProposals.length > 0 ? selectedProposals : filteredProposals.map(p => p.id),
        format: format,
        filters: searchFilters
      };
      
      const response = await fetch('/api/v1/proposals/bulk-export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(exportData)
      });
      
      if (!response.ok) {
        throw new Error('Export failed');
      }
      
      // Handle file download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `proposals_export.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (status.toLowerCase()) {
      case 'draft': return 'default';
      case 'in_review': return 'info';
      case 'approved': return 'success';
      case 'rejected': return 'error';
      case 'completed': return 'primary';
      default: return 'default';
    }
  };

  const getPriorityColor = (priority?: string): 'default' | 'error' | 'warning' | 'success' => {
    switch (priority) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  const renderSearchAndFilters = (): JSX.Element => (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              placeholder="Search proposals..."
              value={searchFilters.text_search}
              onChange={(e) => handleSearch(e.target.value)}
              InputProps={{
                startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
              }}
            />
          </Grid>
          
          <Grid item xs={12} md={8}>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
              <Button
                variant="outlined"
                startIcon={<FilterIcon />}
                onClick={() => setFilterDialogOpen(true)}
                sx={{ minWidth: 120 }}
              >
                Filters
                {(searchFilters.status_filter.length + searchFilters.phase_filter.length + 
                  searchFilters.client_filter.length + searchFilters.assigned_user.length + 
                  searchFilters.tags.length + searchFilters.priority.length) > 0 && (
                  <Badge
                    badgeContent={
                      searchFilters.status_filter.length + searchFilters.phase_filter.length + 
                      searchFilters.client_filter.length + searchFilters.assigned_user.length + 
                      searchFilters.tags.length + searchFilters.priority.length
                    }
                    color="primary"
                    sx={{ ml: 1 }}
                  />
                )}
              </Button>
              
              <Button
                variant="outlined"
                startIcon={<SortIcon />}
                onClick={(e) => setSortMenuAnchor(e.currentTarget)}
              >
                Sort
              </Button>
              
              <Button
                variant="outlined"
                startIcon={<CompareIcon />}
                onClick={handleCompareProposals}
                disabled={selectedProposals.length < 2}
              >
                Compare ({selectedProposals.length})
              </Button>
              
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={(e) => setExportMenuAnchor(e.currentTarget)}
                disabled={filteredProposals.length === 0}
              >
                Export
              </Button>
              
              <Button
                variant="outlined"
                startIcon={<ClearIcon />}
                onClick={clearFilters}
              >
                Clear
              </Button>
              
              <IconButton onClick={loadProposals}>
                <RefreshIcon />
              </IconButton>
            </Box>
          </Grid>
        </Grid>
        
        {/* Active Filters Display */}
        {(searchFilters.status_filter.length > 0 || searchFilters.phase_filter.length > 0 || 
          searchFilters.client_filter.length > 0 || searchFilters.tags.length > 0) && (
          <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {searchFilters.status_filter.map(status => (
              <Chip
                key={status}
                label={`Status: ${status}`}
                onDelete={() => handleFilterChange('status_filter', 
                  searchFilters.status_filter.filter(s => s !== status)
                )}
                size="small"
              />
            ))}
            {searchFilters.phase_filter.map(phase => (
              <Chip
                key={phase}
                label={`Phase: ${phase}`}
                onDelete={() => handleFilterChange('phase_filter', 
                  searchFilters.phase_filter.filter(p => p !== phase)
                )}
                size="small"
              />
            ))}
            {searchFilters.client_filter.map(client => (
              <Chip
                key={client}
                label={`Client: ${client}`}
                onDelete={() => handleFilterChange('client_filter', 
                  searchFilters.client_filter.filter(c => c !== client)
                )}
                size="small"
              />
            ))}
            {searchFilters.tags.map(tag => (
              <Chip
                key={tag}
                label={`Tag: ${tag}`}
                onDelete={() => handleFilterChange('tags', 
                  searchFilters.tags.filter(t => t !== tag)
                )}
                size="small"
              />
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );

  const renderProposalsTable = (): JSX.Element => (
    <Card>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  indeterminate={selectedProposals.length > 0 && selectedProposals.length < filteredProposals.length}
                  checked={filteredProposals.length > 0 && selectedProposals.length === filteredProposals.length}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                />
              </TableCell>
              <TableCell>Title</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Phase</TableCell>
              <TableCell>Client</TableCell>
              <TableCell>Assigned To</TableCell>
              <TableCell>Priority</TableCell>
              <TableCell>Value</TableCell>
              <TableCell>Progress</TableCell>
              <TableCell>Updated</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredProposals.map((proposal) => (
              <TableRow key={proposal.id} hover>
                <TableCell padding="checkbox">
                  <Checkbox
                    checked={selectedProposals.includes(proposal.id)}
                    onChange={(e) => handleProposalSelection(proposal.id, e.target.checked)}
                  />
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <IconButton
                      size="small"
                      onClick={() => toggleFavorite(proposal.id)}
                    >
                      {favoriteProposals.includes(proposal.id) ? (
                        <StarIcon color="warning" />
                      ) : (
                        <StarBorderIcon />
                      )}
                    </IconButton>
                    <Typography variant="body2" fontWeight="medium">
                      {proposal.title}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip
                    label={proposal.status}
                    color={getStatusColor(proposal.status)}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Chip label={proposal.phase} variant="outlined" size="small" />
                </TableCell>
                <TableCell>{proposal.client_name || '-'}</TableCell>
                <TableCell>{proposal.assigned_to || '-'}</TableCell>
                <TableCell>
                  {proposal.priority && (
                    <Chip
                      label={proposal.priority}
                      color={getPriorityColor(proposal.priority)}
                      size="small"
                      variant="outlined"
                    />
                  )}
                </TableCell>
                <TableCell>
                  {proposal.estimated_value ? `$${proposal.estimated_value.toLocaleString()}` : '-'}
                </TableCell>
                <TableCell>
                  {proposal.completion_percentage !== undefined && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Box sx={{ width: 60 }}>
                        <LinearProgress
                          variant="determinate"
                          value={proposal.completion_percentage}
                          sx={{ height: 6, borderRadius: 3 }}
                        />
                      </Box>
                      <Typography variant="caption">
                        {proposal.completion_percentage}%
                      </Typography>
                    </Box>
                  )}
                </TableCell>
                <TableCell>
                  {new Date(proposal.updated_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    <Tooltip title="View">
                      <IconButton size="small">
                        <ViewIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Edit">
                      <IconButton size="small">
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Share">
                      <IconButton size="small">
                        <ShareIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      
      {/* Pagination */}
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'center' }}>
        <Pagination
          count={Math.ceil(totalItems / itemsPerPage)}
          page={currentPage}
          onChange={(_, page) => setCurrentPage(page)}
          color="primary"
        />
      </Box>
    </Card>
  );

  if (loading && proposals.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h4" gutterBottom>
            Proposal Database
          </Typography>
          <Typography variant="body1" color="textSecondary">
            Advanced search, filtering, and analysis of all proposals
          </Typography>
        </Box>

        {/* Error Alert */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Search and Filters */}
        {renderSearchAndFilters()}

        {/* Main Content */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
          <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
            <Tab label={`All Proposals (${filteredProposals.length})`} />
            <Tab label="Analytics" />
            <Tab label="Templates" />
            <Tab label="Workflows" />
          </Tabs>
        </Box>

        {activeTab === 0 && renderProposalsTable()}
        {activeTab === 1 && (
          <Card>
            <CardContent>
              <Typography variant="h6">Analytics Dashboard</Typography>
              <Typography variant="body2" color="textSecondary">
                Proposal analytics and insights will be displayed here.
              </Typography>
            </CardContent>
          </Card>
        )}
        {activeTab === 2 && (
          <Card>
            <CardContent>
              <Typography variant="h6">Template Management</Typography>
              <Typography variant="body2" color="textSecondary">
                Proposal templates and template management will be displayed here.
              </Typography>
            </CardContent>
          </Card>
        )}
        {activeTab === 3 && (
          <Card>
            <CardContent>
              <Typography variant="h6">Workflow Management</Typography>
              <Typography variant="body2" color="textSecondary">
                Proposal workflows and automation will be displayed here.
              </Typography>
            </CardContent>
          </Card>
        )}

        {/* Filter Dialog */}
        <Dialog open={filterDialogOpen} onClose={() => setFilterDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle>Advanced Filters</DialogTitle>
          <DialogContent>
            <Grid container spacing={2} sx={{ pt: 2 }}>
              <Grid item xs={12} md={6}>
                <Autocomplete
                  multiple
                  options={statusOptions}
                  value={searchFilters.status_filter}
                  onChange={(_, value) => handleFilterChange('status_filter', value)}
                  renderInput={(params) => <TextField {...params} label="Status" />}
                />
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Autocomplete
                  multiple
                  options={phaseOptions}
                  value={searchFilters.phase_filter}
                  onChange={(_, value) => handleFilterChange('phase_filter', value)}
                  renderInput={(params) => <TextField {...params} label="Phase" />}
                />
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Autocomplete
                  multiple
                  options={clientOptions}
                  value={searchFilters.client_filter}
                  onChange={(_, value) => handleFilterChange('client_filter', value)}
                  renderInput={(params) => <TextField {...params} label="Client" />}
                />
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Autocomplete
                  multiple
                  options={userOptions}
                  value={searchFilters.assigned_user}
                  onChange={(_, value) => handleFilterChange('assigned_user', value)}
                  renderInput={(params) => <TextField {...params} label="Assigned User" />}
                />
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Autocomplete
                  multiple
                  options={tagOptions}
                  value={searchFilters.tags}
                  onChange={(_, value) => handleFilterChange('tags', value)}
                  renderInput={(params) => <TextField {...params} label="Tags" />}
                />
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Autocomplete
                  multiple
                  options={priorityOptions}
                  value={searchFilters.priority}
                  onChange={(_, value) => handleFilterChange('priority', value)}
                  renderInput={(params) => <TextField {...params} label="Priority" />}
                />
              </Grid>
              
              <Grid item xs={12} md={6}>
                <MuiDatePicker
                  label="Date From"
                  value={searchFilters.date_from || null}
                  onChange={(date) => handleFilterChange('date_from', date)}
                  renderInput={(params) => <TextField {...params} fullWidth />}
                />
              </Grid>
              
              <Grid item xs={12} md={6}>
                <MuiDatePicker
                  label="Date To"
                  value={searchFilters.date_to || null}
                  onChange={(date) => handleFilterChange('date_to', date)}
                  renderInput={(params) => <TextField {...params} fullWidth />}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={clearFilters}>Clear All</Button>
            <Button onClick={() => setFilterDialogOpen(false)}>Close</Button>
          </DialogActions>
        </Dialog>

        {/* Sort Menu */}
        <Menu
          anchorEl={sortMenuAnchor}
          open={Boolean(sortMenuAnchor)}
          onClose={() => setSortMenuAnchor(null)}
        >
          <MenuItem onClick={() => {
            handleFilterChange('sort_by', 'title');
            handleFilterChange('sort_order', 'asc');
            setSortMenuAnchor(null);
          }}>
            Title (A-Z)
          </MenuItem>
          <MenuItem onClick={() => {
            handleFilterChange('sort_by', 'created_at');
            handleFilterChange('sort_order', 'desc');
            setSortMenuAnchor(null);
          }}>
            Newest First
          </MenuItem>
          <MenuItem onClick={() => {
            handleFilterChange('sort_by', 'updated_at');
            handleFilterChange('sort_order', 'desc');
            setSortMenuAnchor(null);
          }}>
            Recently Updated
          </MenuItem>
          <MenuItem onClick={() => {
            handleFilterChange('sort_by', 'estimated_value');
            handleFilterChange('sort_order', 'desc');
            setSortMenuAnchor(null);
          }}>
            Highest Value
          </MenuItem>
        </Menu>

        {/* Export Menu */}
        <Menu
          anchorEl={exportMenuAnchor}
          open={Boolean(exportMenuAnchor)}
          onClose={() => setExportMenuAnchor(null)}
        >
          <MenuItem onClick={() => {
            handleBulkExport('csv');
            setExportMenuAnchor(null);
          }}>
            <ListItemIcon><DownloadIcon /></ListItemIcon>
            <ListItemText>Export as CSV</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => {
            handleBulkExport('xlsx');
            setExportMenuAnchor(null);
          }}>
            <ListItemIcon><DownloadIcon /></ListItemIcon>
            <ListItemText>Export as Excel</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => {
            handleBulkExport('pdf');
            setExportMenuAnchor(null);
          }}>
            <ListItemIcon><DownloadIcon /></ListItemIcon>
            <ListItemText>Export as PDF</ListItemText>
          </MenuItem>
        </Menu>

        {/* Comparison Dialog */}
        <Dialog open={comparisonDialogOpen} onClose={() => setComparisonDialogOpen(false)} maxWidth="lg" fullWidth>
          <DialogTitle>Proposal Comparison</DialogTitle>
          <DialogContent>
            {comparisonData && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Comparing {comparisonData.proposals.length} Proposals
                </Typography>
                
                <Grid container spacing={2}>
                  {comparisonData.proposals.map((proposal) => (
                    <Grid item xs={12} md={6} lg={4} key={proposal.id}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle1" gutterBottom>
                            {proposal.title}
                          </Typography>
                          <Box sx={{ mb: 1 }}>
                            <Chip label={proposal.status} color={getStatusColor(proposal.status)} size="small" />
                          </Box>
                          <Typography variant="body2" color="textSecondary">
                            Phase: {proposal.phase}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            Value: {proposal.estimated_value ? `$${proposal.estimated_value.toLocaleString()}` : 'N/A'}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            Progress: {proposal.completion_percentage || 0}%
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
                
                <Divider sx={{ my: 3 }} />
                
                <Typography variant="h6" gutterBottom>
                  Comparison Metrics
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={4}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="h6">
                          {comparisonData.comparison_metrics.average_completion_time?.toFixed(1) || 0}%
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          Average Progress
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="h6">
                          ${comparisonData.comparison_metrics.total_estimated_value?.toLocaleString() || 0}
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          Total Estimated Value
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="h6">
                          {Object.keys(comparisonData.comparison_metrics.status_distribution || {}).length}
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          Different Statuses
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setComparisonDialogOpen(false)}>Close</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
};

export default ProposalDatabaseInterface; 