import React, { useState, useCallback, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Divider,
  Grid
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  InsertDriveFile as FileIcon,
  Image as ImageIcon,
  Description as DocumentIcon,
  TableChart as SpreadsheetIcon,
  Slideshow as PresentationIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Info as InfoIcon
} from '@mui/icons-material';

// Types
interface FileUploadProps {
  proposalId?: string;
  onUploadComplete?: (files: UploadedFile[]) => void;
  maxFiles?: number;
  maxFileSize?: number;
  allowedTypes?: string[];
}

interface UploadedFile {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'uploading' | 'ready' | 'error';
  progress?: number;
  error_message?: string;
}

interface FileUploadRequest {
  filename: string;
  file_type: 'image' | 'document' | 'spreadsheet' | 'presentation' | 'transcript';
  proposal_id?: string;
  is_public: boolean;
  description?: string;
}

const FileUpload: React.FC<FileUploadProps> = ({
  proposalId,
  onUploadComplete,
  maxFiles = 10,
  maxFileSize = 50 * 1024 * 1024, // 50MB
  allowedTypes = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.pdf', '.doc', '.docx', '.txt', '.rtf', '.xls', '.xlsx', '.csv', '.ppt', '.pptx']
}) => {
  // State management
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Dialog states
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [uploadSettings, setUploadSettings] = useState({
    is_public: false,
    description: '',
    auto_attach: true
  });

  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);

  // File type mapping
  const getFileType = (filename: string): 'image' | 'document' | 'spreadsheet' | 'presentation' | 'transcript' => {
    const extension = filename.toLowerCase().split('.').pop() || '';
    
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(extension)) {
      return 'image';
    } else if (['xls', 'xlsx', 'csv'].includes(extension)) {
      return 'spreadsheet';
    } else if (['ppt', 'pptx'].includes(extension)) {
      return 'presentation';
    } else if (['txt', 'docx', 'pdf'].includes(extension) && filename.toLowerCase().includes('transcript')) {
      return 'transcript';
    } else {
      return 'document';
    }
  };

  const getFileIcon = (fileType: string): JSX.Element => {
    switch (fileType) {
      case 'image':
        return <ImageIcon color="primary" />;
      case 'spreadsheet':
        return <SpreadsheetIcon color="success" />;
      case 'presentation':
        return <PresentationIcon color="warning" />;
      case 'document':
      case 'transcript':
        return <DocumentIcon color="info" />;
      default:
        return <FileIcon />;
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const validateFile = (file: File): string | null => {
    // Check file size
    if (file.size > maxFileSize) {
      return `File size (${formatFileSize(file.size)}) exceeds maximum allowed (${formatFileSize(maxFileSize)})`;
    }

    // Check file type
    const extension = '.' + file.name.toLowerCase().split('.').pop();
    if (!allowedTypes.includes(extension)) {
      return `File type ${extension} is not allowed. Allowed types: ${allowedTypes.join(', ')}`;
    }

    // Check total files limit
    if (files.length >= maxFiles) {
      return `Maximum ${maxFiles} files allowed`;
    }

    return null;
  };

  const handleFiles = useCallback((fileList: FileList) => {
    const newFiles: UploadedFile[] = [];
    const errors: string[] = [];

    Array.from(fileList).forEach((file) => {
      const validationError = validateFile(file);
      if (validationError) {
        errors.push(`${file.name}: ${validationError}`);
        return;
      }

      const uploadedFile: UploadedFile = {
        id: `${Date.now()}-${Math.random()}`,
        filename: file.name,
        file_type: getFileType(file.name),
        file_size: file.size,
        status: 'uploading',
        progress: 0
      };

      newFiles.push(uploadedFile);
    });

    if (errors.length > 0) {
      setError(errors.join('\n'));
    }

    if (newFiles.length > 0) {
      setFiles(prev => [...prev, ...newFiles]);
      uploadFiles(Array.from(fileList).filter(file => !validateFile(file)), newFiles);
    }
  }, [files.length, maxFiles, maxFileSize, allowedTypes]);

  const uploadFiles = async (fileList: File[], uploadedFiles: UploadedFile[]): Promise<void> => {
    setUploading(true);
    setError(null);

    const uploadPromises = fileList.map(async (file, index) => {
      const uploadedFile = uploadedFiles[index];
      
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('file_type', getFileType(file.name));
        formData.append('is_public', uploadSettings.is_public.toString());
        
        if (proposalId && uploadSettings.auto_attach) {
          formData.append('proposal_id', proposalId);
        }
        
        if (uploadSettings.description) {
          formData.append('description', uploadSettings.description);
        }

        const response = await fetch('/api/v1/files/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: formData
        });

        if (!response.ok) {
          throw new Error(`Upload failed: ${response.statusText}`);
        }

        const result = await response.json();
        
        if (result.success) {
          setFiles(prev => prev.map(f => 
            f.id === uploadedFile.id 
              ? { ...f, status: 'ready', progress: 100, id: result.file_id }
              : f
          ));
        } else {
          throw new Error(result.message || 'Upload failed');
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Upload failed';
        setFiles(prev => prev.map(f => 
          f.id === uploadedFile.id 
            ? { ...f, status: 'error', error_message: errorMessage }
            : f
        ));
      }
    });

    await Promise.all(uploadPromises);
    setUploading(false);

    // Check if all uploads completed successfully
    const completedFiles = files.filter(f => f.status === 'ready');
    if (completedFiles.length > 0 && onUploadComplete) {
      onUploadComplete(completedFiles);
    }

    setSuccess(`Successfully uploaded ${completedFiles.length} file(s)`);
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  }, [handleFiles]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  }, [handleFiles]);

  const removeFile = (fileId: string): void => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const clearAll = (): void => {
    setFiles([]);
    setError(null);
    setSuccess(null);
  };

  return (
    <Box>
      {/* Upload Area */}
      <Card
        sx={{
          border: dragActive ? '2px dashed #1976d2' : '2px dashed #ccc',
          backgroundColor: dragActive ? '#f3f4f6' : 'transparent',
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          '&:hover': {
            borderColor: '#1976d2',
            backgroundColor: '#f9f9f9'
          }
        }}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <CardContent sx={{ textAlign: 'center', py: 4 }}>
          <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Drop files here or click to browse
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            Maximum {maxFiles} files, up to {formatFileSize(maxFileSize)} each
          </Typography>
          <Typography variant="caption" color="textSecondary">
            Supported formats: {allowedTypes.join(', ')}
          </Typography>
        </CardContent>
      </Card>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={allowedTypes.join(',')}
        onChange={handleFileInput}
        style={{ display: 'none' }}
      />

      {/* Upload Settings */}
      <Box sx={{ mt: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
        <Button
          variant="outlined"
          size="small"
          onClick={() => setSettingsDialogOpen(true)}
        >
          Upload Settings
        </Button>
        
        {files.length > 0 && (
          <Button
            variant="outlined"
            size="small"
            color="error"
            onClick={clearAll}
          >
            Clear All
          </Button>
        )}
        
        <Box sx={{ flexGrow: 1 }} />
        
        <Typography variant="caption" color="textSecondary">
          {files.length} / {maxFiles} files
        </Typography>
      </Box>

      {/* Status Messages */}
      {error && (
        <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mt: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* File List */}
      {files.length > 0 && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Files ({files.length})
            </Typography>
            <List>
              {files.map((file, index) => (
                <React.Fragment key={file.id}>
                  <ListItem>
                    <ListItemIcon>
                      {file.status === 'ready' ? (
                        <CheckIcon color="success" />
                      ) : file.status === 'error' ? (
                        <ErrorIcon color="error" />
                      ) : (
                        getFileIcon(file.file_type)
                      )}
                    </ListItemIcon>
                    
                    <ListItemText
                      primary={file.filename}
                      secondary={
                        <Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Chip
                              label={file.file_type}
                              size="small"
                              variant="outlined"
                            />
                            <Typography variant="caption">
                              {formatFileSize(file.file_size)}
                            </Typography>
                          </Box>
                          
                          {file.status === 'uploading' && (
                            <LinearProgress
                              variant="determinate"
                              value={file.progress || 0}
                              sx={{ width: '100%' }}
                            />
                          )}
                          
                          {file.status === 'error' && (
                            <Typography variant="caption" color="error">
                              {file.error_message}
                            </Typography>
                          )}
                          
                          {file.status === 'ready' && (
                            <Typography variant="caption" color="success.main">
                              Upload complete
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                    
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        onClick={() => removeFile(file.id)}
                        disabled={file.status === 'uploading'}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                  {index < files.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Upload Settings Dialog */}
      <Dialog
        open={settingsDialogOpen}
        onClose={() => setSettingsDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Upload Settings</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={uploadSettings.is_public}
                      onChange={(e) => setUploadSettings({
                        ...uploadSettings,
                        is_public: e.target.checked
                      })}
                    />
                  }
                  label="Make files publicly accessible"
                />
              </Grid>
              
              {proposalId && (
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={uploadSettings.auto_attach}
                        onChange={(e) => setUploadSettings({
                          ...uploadSettings,
                          auto_attach: e.target.checked
                        })}
                      />
                    }
                    label="Automatically attach to current proposal"
                  />
                </Grid>
              )}
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Description (optional)"
                  multiline
                  rows={3}
                  value={uploadSettings.description}
                  onChange={(e) => setUploadSettings({
                    ...uploadSettings,
                    description: e.target.value
                  })}
                  helperText="Add a description for all uploaded files"
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSettingsDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Upload Progress Indicator */}
      {uploading && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" gutterBottom>
            Uploading files...
          </Typography>
          <LinearProgress />
        </Box>
      )}
    </Box>
  );
};

export default FileUpload; 