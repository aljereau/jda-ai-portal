import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
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
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Checkbox,
  FormControlLabel,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  LinearProgress,
  Tooltip
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Assignment as AssignmentIcon,
  Analytics as AnalyticsIcon,
  People as PeopleIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  FilterList as FilterIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon
} from '@mui/icons-material';

// Types
interface DashboardMetric {
  label: string;
  value: number;
  change?: number;
  change_type?: string;
  format_type: string;
}

interface TeamAnalytics {
  total_proposals: number;
  active_proposals: number;
  completed_proposals: number;
  proposals_this_month: number;
  average_completion_time?: number;
  team_productivity: Record<string, any>;
  proposal_status_distribution: Record<string, number>;
  monthly_trends: Array<{
    month: string;
    month_name: string;
    proposals_created: number;
  }>;
}

interface DashboardOverview {
  metrics: DashboardMetric[];
  recent_proposals: ProposalSummary[];
  team_analytics: TeamAnalytics;
  user_activity: Array<{
    type: string;
    user_name: string;
    action: string;
    timestamp: string;
    proposal_id?: string;
  }>;
  system_status: Record<string, any>;
}

interface ProposalSummary {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  creator_name: string;
  phase: string;
}

interface ProposalAssignment {
  proposal_id: string;
  user_id: string;
  notes?: string;
}

interface BulkUpdateOperation {
  operation_type: string;
  proposal_ids: string[];
  update_data: Record<string, any>;
}

const TeamDashboard: React.FC = () => {
  // State management
  const [activeTab, setActiveTab] = useState(0);
  const [dashboardData, setDashboardData] = useState<DashboardOverview | null>(null);
  const [proposals, setProposals] = useState<ProposalSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Dialog states
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [bulkUpdateDialogOpen, setBulkUpdateDialogOpen] = useState(false);
  const [selectedProposal, setSelectedProposal] = useState<ProposalSummary | null>(null);
  const [selectedProposals, setSelectedProposals] = useState<string[]>([]);
  
  // Form states
  const [assignmentData, setAssignmentData] = useState<ProposalAssignment>({
    proposal_id: '',
    user_id: '',
    notes: ''
  });
  const [bulkOperation, setBulkOperation] = useState<BulkUpdateOperation>({
    operation_type: 'status_update',
    proposal_ids: [],
    update_data: {}
  });
  
  // Filter states
  const [statusFilter, setStatusFilter] = useState('');
  const [assignedToFilter, setAssignedToFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Load dashboard data on component mount
  useEffect(() => {
    loadDashboardData();
    loadProposals();
  }, []);

  const loadDashboardData = async (): Promise<void> => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/team-dashboard/overview', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to load dashboard data');
      }
      
      const data = await response.json();
      setDashboardData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const loadProposals = async (): Promise<void> => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append('status_filter', statusFilter);
      if (assignedToFilter) params.append('assigned_to_id', assignedToFilter);
      if (searchTerm) params.append('search', searchTerm);
      
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load proposals');
    }
  };

  const handleAssignProposal = async (): Promise<void> => {
    try {
      const response = await fetch('/api/v1/team-dashboard/assign-proposal', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(assignmentData)
      });
      
      if (!response.ok) {
        throw new Error('Failed to assign proposal');
      }
      
      const result = await response.json();
      if (result.success) {
        setAssignDialogOpen(false);
        loadProposals();
        setAssignmentData({ proposal_id: '', user_id: '', notes: '' });
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign proposal');
    }
  };

  const handleBulkUpdate = async (): Promise<void> => {
    try {
      const operation = {
        ...bulkOperation,
        proposal_ids: selectedProposals
      };
      
      const response = await fetch('/api/v1/team-dashboard/bulk-update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(operation)
      });
      
      if (!response.ok) {
        throw new Error('Failed to perform bulk update');
      }
      
      const result = await response.json();
      if (result.success) {
        setBulkUpdateDialogOpen(false);
        loadProposals();
        setSelectedProposals([]);
        setBulkOperation({
          operation_type: 'status_update',
          proposal_ids: [],
          update_data: {}
        });
      } else {
        setError(`Bulk update completed with errors: ${result.errors.join(', ')}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to perform bulk update');
    }
  };

  const formatMetricValue = (metric: DashboardMetric): string => {
    switch (metric.format_type) {
      case 'percentage':
        return `${metric.value}%`;
      case 'currency':
        return `$${metric.value.toLocaleString()}`;
      default:
        return metric.value.toLocaleString();
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

  const renderOverviewTab = (): JSX.Element => (
    <Box>
      {/* Key Metrics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {dashboardData?.metrics.map((metric, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom variant="body2">
                  {metric.label}
                </Typography>
                <Typography variant="h4" component="div">
                  {formatMetricValue(metric)}
                </Typography>
                {metric.change !== undefined && (
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                    {metric.change_type === 'increase' ? (
                      <TrendingUpIcon color="success" fontSize="small" />
                    ) : (
                      <TrendingDownIcon color="error" fontSize="small" />
                    )}
                    <Typography
                      variant="body2"
                      color={metric.change_type === 'increase' ? 'success.main' : 'error.main'}
                      sx={{ ml: 0.5 }}
                    >
                      {metric.change > 0 ? '+' : ''}{metric.change}%
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Recent Proposals and Activity */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Proposals
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Title</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Creator</TableCell>
                      <TableCell>Updated</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {dashboardData?.recent_proposals.slice(0, 5).map((proposal) => (
                      <TableRow key={proposal.id}>
                        <TableCell>{proposal.title}</TableCell>
                        <TableCell>
                          <Chip
                            label={proposal.status}
                            color={getStatusColor(proposal.status)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{proposal.creator_name}</TableCell>
                        <TableCell>
                          {new Date(proposal.updated_at).toLocaleDateString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Activity
              </Typography>
              <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                {dashboardData?.user_activity.slice(0, 10).map((activity, index) => (
                  <Box key={index} sx={{ mb: 2, pb: 1, borderBottom: '1px solid #eee' }}>
                    <Typography variant="body2" fontWeight="medium">
                      {activity.user_name}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      {activity.action}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {new Date(activity.timestamp).toLocaleString()}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );

  const renderProposalsTab = (): JSX.Element => (
    <Box>
      {/* Filters and Actions */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <TextField
          label="Search"
          variant="outlined"
          size="small"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          sx={{ minWidth: 200 }}
        />
        
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Status</InputLabel>
          <Select
            value={statusFilter}
            label="Status"
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="draft">Draft</MenuItem>
            <MenuItem value="in_review">In Review</MenuItem>
            <MenuItem value="approved">Approved</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
          </Select>
        </FormControl>
        
        <Button
          variant="outlined"
          startIcon={<FilterIcon />}
          onClick={loadProposals}
        >
          Apply Filters
        </Button>
        
        <Box sx={{ flexGrow: 1 }} />
        
        <Button
          variant="contained"
          startIcon={<AssignmentIcon />}
          onClick={() => setAssignDialogOpen(true)}
          disabled={!selectedProposal}
        >
          Assign
        </Button>
        
        <Button
          variant="outlined"
          startIcon={<EditIcon />}
          onClick={() => setBulkUpdateDialogOpen(true)}
          disabled={selectedProposals.length === 0}
        >
          Bulk Update ({selectedProposals.length})
        </Button>
        
        <IconButton onClick={loadProposals}>
          <RefreshIcon />
        </IconButton>
      </Box>

      {/* Proposals Table */}
      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={selectedProposals.length > 0 && selectedProposals.length < proposals.length}
                    checked={proposals.length > 0 && selectedProposals.length === proposals.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedProposals(proposals.map(p => p.id));
                      } else {
                        setSelectedProposals([]);
                      }
                    }}
                  />
                </TableCell>
                <TableCell>Title</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Phase</TableCell>
                <TableCell>Creator</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Updated</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {proposals.map((proposal) => (
                <TableRow key={proposal.id} hover>
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selectedProposals.includes(proposal.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedProposals([...selectedProposals, proposal.id]);
                        } else {
                          setSelectedProposals(selectedProposals.filter(id => id !== proposal.id));
                        }
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {proposal.title}
                    </Typography>
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
                  <TableCell>{proposal.creator_name}</TableCell>
                  <TableCell>
                    {new Date(proposal.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {new Date(proposal.updated_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Assign Proposal">
                      <IconButton
                        size="small"
                        onClick={() => {
                          setSelectedProposal(proposal);
                          setAssignmentData({
                            ...assignmentData,
                            proposal_id: proposal.id
                          });
                          setAssignDialogOpen(true);
                        }}
                      >
                        <AssignmentIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
    </Box>
  );

  const renderAnalyticsTab = (): JSX.Element => (
    <Box>
      {dashboardData?.team_analytics && (
        <Grid container spacing={3}>
          {/* Status Distribution */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Proposal Status Distribution
                </Typography>
                {Object.entries(dashboardData.team_analytics.proposal_status_distribution).map(([status, count]) => (
                  <Box key={status} sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2">{status}</Typography>
                      <Typography variant="body2">{count}</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={(count / dashboardData.team_analytics.total_proposals) * 100}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </Box>
                ))}
              </CardContent>
            </Card>
          </Grid>

          {/* Monthly Trends */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Monthly Trends
                </Typography>
                {dashboardData.team_analytics.monthly_trends.map((trend, index) => (
                  <Box key={index} sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2">{trend.month_name}</Typography>
                      <Typography variant="body2">{trend.proposals_created}</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={Math.min((trend.proposals_created / 10) * 100, 100)}
                      sx={{ height: 6, borderRadius: 3 }}
                    />
                  </Box>
                ))}
              </CardContent>
            </Card>
          </Grid>

          {/* Team Productivity */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Team Productivity
                </Typography>
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Team Member</TableCell>
                        <TableCell>Total Proposals</TableCell>
                        <TableCell>Active Proposals</TableCell>
                        <TableCell>Completion Rate</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(dashboardData.team_analytics.team_productivity).map(([member, data]: [string, any]) => (
                        <TableRow key={member}>
                          <TableCell>{member}</TableCell>
                          <TableCell>{data.total_proposals}</TableCell>
                          <TableCell>{data.active_proposals}</TableCell>
                          <TableCell>
                            {data.total_proposals > 0 
                              ? `${Math.round(((data.total_proposals - data.active_proposals) / data.total_proposals) * 100)}%`
                              : '0%'
                            }
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Team Dashboard
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Manage proposals, track team performance, and analyze project metrics
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Main Content */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
          <Tab icon={<DashboardIcon />} label="Overview" />
          <Tab icon={<AssignmentIcon />} label="Proposals" />
          <Tab icon={<AnalyticsIcon />} label="Analytics" />
        </Tabs>
      </Box>

      {activeTab === 0 && renderOverviewTab()}
      {activeTab === 1 && renderProposalsTab()}
      {activeTab === 2 && renderAnalyticsTab()}

      {/* Assignment Dialog */}
      <Dialog open={assignDialogOpen} onClose={() => setAssignDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Assign Proposal</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>User</InputLabel>
              <Select
                value={assignmentData.user_id}
                label="User"
                onChange={(e) => setAssignmentData({
                  ...assignmentData,
                  user_id: e.target.value
                })}
              >
                <MenuItem value="user1">John Doe</MenuItem>
                <MenuItem value="user2">Jane Smith</MenuItem>
                <MenuItem value="user3">Bob Johnson</MenuItem>
              </Select>
            </FormControl>
            
            <TextField
              fullWidth
              label="Notes"
              multiline
              rows={3}
              value={assignmentData.notes}
              onChange={(e) => setAssignmentData({
                ...assignmentData,
                notes: e.target.value
              })}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAssignDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleAssignProposal} variant="contained">
            Assign
          </Button>
        </DialogActions>
      </Dialog>

      {/* Bulk Update Dialog */}
      <Dialog open={bulkUpdateDialogOpen} onClose={() => setBulkUpdateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Bulk Update Proposals</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Operation</InputLabel>
              <Select
                value={bulkOperation.operation_type}
                label="Operation"
                onChange={(e) => setBulkOperation({
                  ...bulkOperation,
                  operation_type: e.target.value
                })}
              >
                <MenuItem value="status_update">Update Status</MenuItem>
                <MenuItem value="assignment">Assign to User</MenuItem>
                <MenuItem value="delete">Delete</MenuItem>
              </Select>
            </FormControl>
            
            {bulkOperation.operation_type === 'status_update' && (
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>New Status</InputLabel>
                <Select
                  value={bulkOperation.update_data.status || ''}
                  label="New Status"
                  onChange={(e) => setBulkOperation({
                    ...bulkOperation,
                    update_data: { ...bulkOperation.update_data, status: e.target.value }
                  })}
                >
                  <MenuItem value="draft">Draft</MenuItem>
                  <MenuItem value="in_review">In Review</MenuItem>
                  <MenuItem value="approved">Approved</MenuItem>
                  <MenuItem value="completed">Completed</MenuItem>
                </Select>
              </FormControl>
            )}
            
            {bulkOperation.operation_type === 'assignment' && (
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Assign to User</InputLabel>
                <Select
                  value={bulkOperation.update_data.assigned_to_id || ''}
                  label="Assign to User"
                  onChange={(e) => setBulkOperation({
                    ...bulkOperation,
                    update_data: { ...bulkOperation.update_data, assigned_to_id: e.target.value }
                  })}
                >
                  <MenuItem value="user1">John Doe</MenuItem>
                  <MenuItem value="user2">Jane Smith</MenuItem>
                  <MenuItem value="user3">Bob Johnson</MenuItem>
                </Select>
              </FormControl>
            )}
            
            <Typography variant="body2" color="textSecondary">
              This will affect {selectedProposals.length} selected proposals.
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBulkUpdateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleBulkUpdate} variant="contained" color="primary">
            Update
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TeamDashboard; 