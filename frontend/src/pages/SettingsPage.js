import React, { useState, useContext, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { deleteAllTransactions, backupDatabase, restoreDatabase } from '../lib/api';
import { AuthContext } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { AlertTriangle, Trash2, User, Download, Upload, Database } from 'lucide-react';
import { toast } from 'sonner';

const SettingsPage = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false);
  const [confirmationText, setConfirmationText] = useState('');
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [backupLoading, setBackupLoading] = useState(false);
  const [restoreLoading, setRestoreLoading] = useState(false);
  const restoreFileInputRef = useRef(null);

  const handleDeleteAll = async () => {
    if (confirmationText.trim().toUpperCase() !== 'DELETE ALL') {
      toast.error('Please type DELETE ALL exactly');
      return;
    }

    setLoading(true);
    try {
      const response = await deleteAllTransactions({ confirmation_text: confirmationText });
      toast.success(`Successfully deleted ${response.data.deleted_count} transactions`);
      setDeleteDialogOpen(false);
      setConfirmationText('');
      setStep(1);
      
      // Redirect to dashboard after deletion
      setTimeout(() => navigate('/'), 1500);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete transactions');
    } finally {
      setLoading(false);
    }
  };

  const handleBackup = async () => {
    setBackupLoading(true);
    try {
      const response = await backupDatabase();
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Extract filename from response headers or create default
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'SpendAlizer-backup.zip';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Backup downloaded successfully!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create backup');
    } finally {
      setBackupLoading(false);
    }
  };

  const handleRestoreFileSelect = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.zip')) {
      toast.error('Please select a valid ZIP backup file');
      return;
    }

    setRestoreLoading(true);
    try {
      const response = await restoreDatabase(file);
      const { restored_counts, backup_metadata, restored_to_user } = response.data;
      
      // Show success message with user info
      const userInfo = restored_to_user ? ` for ${restored_to_user.email}` : '';
      toast.success(
        `Database restored successfully${userInfo}! ` +
        `Restored: ${restored_counts.transactions} transactions, ` +
        `${restored_counts.categories} categories, ${restored_counts.rules} rules, ` +
        `${restored_counts.accounts} accounts`,
        { duration: 5000 }
      );
      
      setRestoreDialogOpen(false);
      
      // Redirect to dashboard after restore with a full reload
      setTimeout(() => {
        window.location.href = '/';
      }, 2000);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to restore database');
    } finally {
      setRestoreLoading(false);
      if (restoreFileInputRef.current) {
        restoreFileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 md:px-8 md:py-12" data-testid="settings-page">
      <div className="mb-8">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-2">Settings</h1>
        <p className="text-muted-foreground">Manage your account and preferences</p>
      </div>

      {/* Profile Section */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
              <User className="w-6 h-6 text-primary" />
            </div>
            <div>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>Your account details</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label className="text-muted-foreground">Name</Label>
            <p className="font-medium">{user?.name}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Email</Label>
            <p className="font-medium">{user?.email}</p>
          </div>
        </CardContent>
      </Card>

      {/* Data Management Section */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center">
              <Database className="w-6 h-6 text-blue-500" />
            </div>
            <div>
              <CardTitle>Data Management</CardTitle>
              <CardDescription>Backup and restore your financial data</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Backup Section */}
          <div className="p-4 rounded-lg border bg-card">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h3 className="font-semibold mb-1 flex items-center gap-2">
                  <Download className="w-4 h-4" />
                  Export Database Backup
                </h3>
                <p className="text-sm text-muted-foreground mb-3">
                  Download a complete backup of all your financial data including transactions, 
                  categories, rules, and accounts as a ZIP file.
                </p>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• All transactions and import history</li>
                  <li>• All categories (system + custom) and rules</li>
                  <li>• Account information</li>
                  <li>• Backup file: SpendAlizer-{'{domain}'}-{'{timestamp}'}.zip</li>
                </ul>
                <p className="text-xs text-muted-foreground mt-2 italic">
                  System categories are included to ensure complete data integrity and proper transaction references.
                </p>
              </div>
            </div>
            <Button
              onClick={handleBackup}
              disabled={backupLoading}
              data-testid="backup-button"
            >
              <Download className="w-4 h-4 mr-2" />
              {backupLoading ? 'Creating Backup...' : 'Download Backup'}
            </Button>
          </div>

          {/* Restore Section */}
          <div className="p-4 rounded-lg border bg-amber-50/50 border-amber-200">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h3 className="font-semibold mb-1 flex items-center gap-2 text-amber-900">
                  <Upload className="w-4 h-4" />
                  Import & Restore Database
                </h3>
                <p className="text-sm text-muted-foreground mb-3">
                  Restore your data from a previous backup. This will replace all current data.
                </p>
                <div className="p-3 rounded bg-amber-100 border border-amber-300 mb-3">
                  <p className="text-sm font-medium text-amber-900 mb-2">⚠️ Important:</p>
                  <ul className="text-sm text-amber-800 space-y-1">
                    <li>• A backup of current data will be created first</li>
                    <li>• All existing data will be replaced with backup data</li>
                    <li>• This process cannot be undone (except via the auto-created backup)</li>
                  </ul>
                </div>
              </div>
            </div>
            <Button
              onClick={() => setRestoreDialogOpen(true)}
              variant="outline"
              className="border-amber-300 hover:bg-amber-50"
              data-testid="restore-button"
            >
              <Upload className="w-4 h-4 mr-2" />
              Restore from Backup
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-destructive">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-destructive" />
            </div>
            <div>
              <CardTitle className="text-destructive">Danger Zone</CardTitle>
              <CardDescription>Irreversible and destructive actions</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="p-4 rounded-lg border-2 border-destructive/20 bg-destructive/5">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="font-semibold text-destructive mb-1">Delete All Transactions</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Permanently delete all your transactions, import history, and related data. 
                  This action cannot be undone.
                </p>
                <ul className="text-sm text-muted-foreground space-y-1 mb-4">
                  <li>• All transactions will be deleted</li>
                  <li>• Import history will be removed</li>
                  <li>• Analytics data will be cleared</li>
                  <li>• Categories and rules will be preserved</li>
                </ul>
              </div>
            </div>
            <Button
              variant="destructive"
              onClick={() => {
                setDeleteDialogOpen(true);
                setStep(1);
                setConfirmationText('');
              }}
              data-testid="delete-all-button"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete All Transactions
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={(open) => {
        if (!open) {
          setDeleteDialogOpen(false);
          setStep(1);
          setConfirmationText('');
        }
      }}>
        <DialogContent data-testid="delete-confirmation-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="w-5 h-5" />
              {step === 1 ? 'Confirm Deletion' : 'Final Confirmation'}
            </DialogTitle>
            <DialogDescription>
              {step === 1 
                ? 'This action cannot be undone. Are you absolutely sure?'
                : 'Type DELETE ALL to confirm this permanent action'
              }
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {step === 1 ? (
              <>
                <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20">
                  <p className="text-sm font-medium text-destructive mb-2">⚠️ Warning:</p>
                  <ul className="text-sm space-y-1">
                    <li>• All your transactions will be permanently deleted</li>
                    <li>• Import history will be removed</li>
                    <li>• This cannot be undone</li>
                    <li>• Analytics will be reset to zero</li>
                  </ul>
                </div>
                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    onClick={() => setDeleteDialogOpen(false)}
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => setStep(2)}
                    className="flex-1"
                    data-testid="proceed-button"
                  >
                    I Understand, Proceed
                  </Button>
                </div>
              </>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="confirmation">
                    Type <code className="px-2 py-1 rounded bg-muted font-mono text-sm">DELETE ALL</code> to confirm
                  </Label>
                  <Input
                    id="confirmation"
                    value={confirmationText}
                    onChange={(e) => setConfirmationText(e.target.value)}
                    placeholder="Type DELETE ALL"
                    data-testid="confirmation-input"
                    className="font-mono"
                  />
                </div>
                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setStep(1);
                      setConfirmationText('');
                    }}
                    className="flex-1"
                  >
                    Back
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={handleDeleteAll}
                    disabled={confirmationText.trim().toUpperCase() !== 'DELETE ALL' || loading}
                    className="flex-1"
                    data-testid="final-delete-button"
                  >
                    {loading ? 'Deleting...' : 'Delete All Transactions'}
                  </Button>
                </div>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Restore Confirmation Dialog */}
      <Dialog open={restoreDialogOpen} onOpenChange={setRestoreDialogOpen}>
        <DialogContent data-testid="restore-confirmation-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-600">
              <AlertTriangle className="w-5 h-5" />
              Restore Database from Backup
            </DialogTitle>
            <DialogDescription>
              This will restore your data from a backup file
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-amber-50 border border-amber-200">
              <p className="text-sm font-medium text-amber-900 mb-2">⚠️ Before proceeding:</p>
              <ul className="text-sm space-y-1 text-amber-800">
                <li>• A backup of your current data will be created automatically</li>
                <li>• All existing data will be replaced with the backup data</li>
                <li>• Only upload backup files created by SpendAlizer</li>
                <li>• The backup file should be a .zip file</li>
              </ul>
            </div>

            <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
              <p className="text-sm font-medium text-blue-900 mb-2">ℹ️ Restoring to: {user?.email}</p>
              <p className="text-xs text-blue-800">
                The backup data will be associated with your current account. If you're restoring 
                a backup from a different environment (e.g., from online to local), the data will 
                appear in your current logged-in account only.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="restore-file">Select Backup File (.zip)</Label>
              <Input
                id="restore-file"
                ref={restoreFileInputRef}
                type="file"
                accept=".zip"
                onChange={handleRestoreFileSelect}
                disabled={restoreLoading}
                data-testid="restore-file-input"
              />
            </div>

            {restoreLoading && (
              <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                <p className="text-sm text-blue-900 font-medium">
                  🔄 Restoring database... This may take a moment.
                </p>
              </div>
            )}

            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setRestoreDialogOpen(false);
                  if (restoreFileInputRef.current) {
                    restoreFileInputRef.current.value = '';
                  }
                }}
                disabled={restoreLoading}
                className="flex-1"
              >
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SettingsPage;
