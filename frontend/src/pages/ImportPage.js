import React, { useState, useEffect, useRef } from 'react';
import { getAccounts, getDataSources, importFile, getImportHistory } from '../lib/api';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Progress } from '../components/ui/progress';
import { Upload, FileText, CheckCircle, XCircle, Clock, Info, Sparkles, User, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

// Import progress steps
const IMPORT_STEPS = [
  { id: 1, name: 'Uploading file', duration: 1000 },
  { id: 2, name: 'Parsing file content', duration: 1500 },
  { id: 3, name: 'Validating transactions', duration: 1000 },
  { id: 4, name: 'Checking for duplicates', duration: 2000 },
  { id: 5, name: 'Applying categorization rules', duration: 2500 },
  { id: 6, name: 'AI categorization (if needed)', duration: 3000 },
  { id: 7, name: 'Saving transactions', duration: 2000 },
  { id: 8, name: 'Finalizing import', duration: 1000 },
];

const ImportPage = () => {
  const [accounts, setAccounts] = useState([]);
  const [dataSources, setDataSources] = useState([]);
  const [history, setHistory] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [selectedDataSource, setSelectedDataSource] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  
  // Progress tracking state
  const [importProgress, setImportProgress] = useState({
    isActive: false,
    currentStep: 0,
    progress: 0,
    stepName: ''
  });
  const progressIntervalRef = useRef(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [accountsRes, sourcesRes, historyRes] = await Promise.all([
        getAccounts(),
        getDataSources(),
        getImportHistory()
      ]);
      setAccounts(accountsRes.data);
      setDataSources(sourcesRes.data);
      setHistory(historyRes.data);
    } catch (error) {
      toast.error('Failed to load import data');
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      const ext = selectedFile.name.split('.').pop().toLowerCase();
      if (['csv', 'xlsx', 'xls'].includes(ext)) {
        setFile(selectedFile);
      } else {
        toast.error('Please select a CSV or XLSX file');
      }
    }
  };

  // Start progress simulation
  const startProgressSimulation = () => {
    let currentStep = 0;
    let stepProgress = 0;
    
    setImportProgress({
      isActive: true,
      currentStep: 1,
      progress: 0,
      stepName: IMPORT_STEPS[0].name
    });

    // Calculate total duration and progress per tick
    const totalSteps = IMPORT_STEPS.length;
    const tickInterval = 100; // Update every 100ms
    
    progressIntervalRef.current = setInterval(() => {
      stepProgress += 5; // Increment within step
      
      if (stepProgress >= 100 && currentStep < totalSteps - 1) {
        // Move to next step
        currentStep++;
        stepProgress = 0;
      }
      
      // Calculate overall progress (0-95%, leave 5% for completion)
      const overallProgress = Math.min(
        ((currentStep * 100 + stepProgress) / (totalSteps * 100)) * 95,
        95
      );
      
      setImportProgress({
        isActive: true,
        currentStep: currentStep + 1,
        progress: overallProgress,
        stepName: IMPORT_STEPS[currentStep]?.name || 'Processing...'
      });
    }, tickInterval);
  };

  // Stop progress simulation
  const stopProgressSimulation = (success = true) => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    
    if (success) {
      // Complete the progress bar
      setImportProgress({
        isActive: true,
        currentStep: IMPORT_STEPS.length,
        progress: 100,
        stepName: 'Complete!'
      });
      
      // Reset after a short delay
      setTimeout(() => {
        setImportProgress({
          isActive: false,
          currentStep: 0,
          progress: 0,
          stepName: ''
        });
      }, 1500);
    } else {
      // Reset immediately on failure
      setImportProgress({
        isActive: false,
        currentStep: 0,
        progress: 0,
        stepName: ''
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !selectedAccount || !selectedDataSource) {
      toast.error('Please fill all fields');
      return;
    }

    setUploading(true);
    startProgressSimulation();
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('account_id', selectedAccount);
    formData.append('data_source', selectedDataSource);

    try {
      const response = await importFile(formData);
      stopProgressSimulation(true);
      toast.success(`Import successful! ${response.data.success_count} transactions imported.`);
      setFile(null);
      setSelectedAccount('');
      setSelectedDataSource('');
      loadData();
    } catch (error) {
      stopProgressSimulation(false);
      toast.error(error.response?.data?.detail || 'Import failed');
    } finally {
      setUploading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'SUCCESS':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'FAILED':
        return <XCircle className="w-5 h-5 text-red-600" />;
      case 'PENDING':
        return <Clock className="w-5 h-5 text-yellow-600" />;
      default:
        return <Clock className="w-5 h-5 text-gray-600" />;
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 md:px-8 md:py-12" data-testid="import-page">
      <div className="mb-8">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-2">Import Transactions</h1>
        <p className="text-muted-foreground">Upload your bank statements to import transactions</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Form and Categorization Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Import Form */}
          <Card data-testid="import-form-card">
          <CardHeader>
            <CardTitle>Upload Statement</CardTitle>
            <CardDescription>Select your account, data source, and file to import</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="account">Account</Label>
                <Select value={selectedAccount} onValueChange={setSelectedAccount}>
                  <SelectTrigger data-testid="account-select">
                    <SelectValue placeholder="Select account" />
                  </SelectTrigger>
                  <SelectContent>
                    {accounts.map((account) => (
                      <SelectItem key={account.id} value={account.id}>
                        {account.name} ({account.institution})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="data-source">Data Source</Label>
                <Select value={selectedDataSource} onValueChange={setSelectedDataSource}>
                  <SelectTrigger data-testid="data-source-select">
                    <SelectValue placeholder="Select data source" />
                  </SelectTrigger>
                  <SelectContent>
                    {dataSources.map((source) => (
                      <SelectItem key={source.id} value={source.id}>
                        {source.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="file">Statement File (CSV/XLSX)</Label>
                <div className="border-2 border-dashed rounded-lg p-8 text-center hover:border-primary transition-colors">
                  <input
                    id="file"
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={handleFileChange}
                    className="hidden"
                    data-testid="file-input"
                  />
                  <label htmlFor="file" className="cursor-pointer">
                    <Upload className="w-12 h-12 mx-auto mb-3 text-muted-foreground" />
                    {file ? (
                      <div>
                        <p className="font-medium">{file.name}</p>
                        <p className="text-sm text-muted-foreground mt-1">
                          {(file.size / 1024).toFixed(2)} KB
                        </p>
                      </div>
                    ) : (
                      <div>
                        <p className="font-medium">Click to upload or drag and drop</p>
                        <p className="text-sm text-muted-foreground mt-1">CSV or XLSX files</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              {/* Progress Indicator */}
              {importProgress.isActive && (
                <div className="space-y-3 p-4 rounded-lg bg-primary/5 border border-primary/20">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-primary" />
                      <span className="font-medium text-primary">{importProgress.stepName}</span>
                    </div>
                    <span className="text-muted-foreground">
                      Step {importProgress.currentStep} of {IMPORT_STEPS.length}
                    </span>
                  </div>
                  <Progress value={importProgress.progress} className="h-2" />
                  <p className="text-xs text-muted-foreground text-center">
                    {Math.round(importProgress.progress)}% complete
                  </p>
                </div>
              )}

              <Button
                type="submit"
                className="w-full"
                disabled={uploading || !file || !selectedAccount || !selectedDataSource}
                data-testid="import-submit-button"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Importing...
                  </>
                ) : (
                  'Import Transactions'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

          {/* How Categorization Works */}
          <Card className="bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Info className="w-5 h-5 text-blue-600" />
              <CardTitle className="text-blue-900 dark:text-blue-100">How Categorization Works</CardTitle>
            </div>
            <CardDescription className="text-blue-700 dark:text-blue-300">
              3-tier automatic categorization system
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <Sparkles className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="font-medium text-sm mb-1">1. Rule-Based Categorization (First Priority)</p>
                  <p className="text-sm text-muted-foreground">
                    Imported transactions are <strong>first</strong> matched against your <strong>categorization rules</strong>. 
                    If a transaction description matches a rule pattern (contains, starts with, etc.), 
                    it's automatically assigned that category. This is the fastest and most accurate method.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <div className="w-5 h-5 rounded bg-gradient-to-r from-pink-500 to-violet-500 flex items-center justify-center">
                    <span className="text-white text-xs font-bold">AI</span>
                  </div>
                </div>
                <div>
                  <p className="font-medium text-sm mb-1">2. AI Categorization (Second Priority)</p>
                  <p className="text-sm text-muted-foreground">
                    If no rules match, the system uses <strong>AI (LLM - Llama3)</strong> to analyze the transaction 
                    description, amount, and direction to intelligently suggest a category. 
                    Requires local Ollama installation.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <User className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <p className="font-medium text-sm mb-1">3. Manual Categorization (Fallback)</p>
                  <p className="text-sm text-muted-foreground">
                    If both rules and AI fail to categorize, transactions remain <strong>Uncategorized</strong>. 
                    You can manually assign categories from the Transactions page and create rules for future automation.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="font-medium text-sm mb-1">4. Continuous Improvement</p>
                  <p className="text-sm text-muted-foreground">
                    The more rules you create, the better the auto-categorization becomes. 
                    Rules are instant and take priority over AI, making your imports faster over time.
                  </p>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-blue-200 dark:border-blue-900 space-y-2">
              <p className="text-xs text-muted-foreground flex items-start gap-2">
                <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>
                  <strong>Priority Order:</strong> Rules → AI → Manual. Rules are checked first for speed and accuracy.
                </span>
              </p>
              <p className="text-xs text-muted-foreground flex items-start gap-2">
                <Sparkles className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>
                  <strong>Pro Tip:</strong> After your first import, review uncategorized transactions 
                  and create rules. Your next import will have much better auto-categorization!
                </span>
              </p>
            </div>
          </CardContent>
        </Card>
        </div>

        {/* Right Column - Import History */}
        <Card data-testid="import-history-card" className="lg:row-span-2">
          <CardHeader>
            <CardTitle>Recent Imports</CardTitle>
            <CardDescription>Your import history</CardDescription>
          </CardHeader>
          <CardContent>
            {history.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">No imports yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {history.slice(0, 10).map((batch) => (
                  <div
                    key={batch.id}
                    className="p-3 rounded-lg border bg-card"
                    data-testid={`import-batch-${batch.id}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{batch.original_file_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(batch.imported_at), 'MMM dd, yyyy HH:mm')}
                        </p>
                      </div>
                      {getStatusIcon(batch.status)}
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-green-600">{batch.success_count} success</span>
                      {batch.duplicate_count > 0 && (
                        <span className="text-yellow-600">{batch.duplicate_count} duplicates</span>
                      )}
                      {batch.error_count > 0 && (
                        <span className="text-red-600">{batch.error_count} errors</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ImportPage;
