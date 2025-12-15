import React, { useState, useEffect, useRef } from 'react';
import { getRules, createRule, deleteRule, getCategories, exportRules, importRules, updateRule } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Trash2, Sparkles, Download, Upload, Pencil } from 'lucide-react';
import { toast } from 'sonner';

const RulesPage = () => {
  const [rules, setRules] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState(null);
  const [formData, setFormData] = useState({
    pattern: '',
    match_type: 'CONTAINS',
    category_id: '',
    priority: 10
  });
  const fileInputRef = useRef(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [rulesRes, catRes] = await Promise.all([
        getRules(),
        getCategories()
      ]);
      setRules(rulesRes.data);
      setCategories(catRes.data);
    } catch (error) {
      toast.error('Failed to load rules');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editMode) {
        await updateRule(editingRuleId, formData);
        toast.success('Rule updated successfully!');
      } else {
        await createRule(formData);
        toast.success('Rule created successfully!');
      }
      setDialogOpen(false);
      setEditMode(false);
      setEditingRuleId(null);
      setFormData({ pattern: '', match_type: 'CONTAINS', category_id: '', priority: 10 });
      loadData();
    } catch (error) {
      toast.error(editMode ? 'Failed to update rule' : 'Failed to create rule');
    }
  };

  const handleEdit = (rule) => {
    setEditMode(true);
    setEditingRuleId(rule.id);
    setFormData({
      pattern: rule.pattern,
      match_type: rule.match_type,
      category_id: rule.category_id,
      priority: rule.priority
    });
    setDialogOpen(true);
  };

  const handleDialogChange = (open) => {
    setDialogOpen(open);
    if (!open) {
      // Reset form when dialog is closed
      setEditMode(false);
      setEditingRuleId(null);
      setFormData({ pattern: '', match_type: 'CONTAINS', category_id: '', priority: 10 });
    }
  };

  const handleDelete = async (ruleId) => {
    try {
      await deleteRule(ruleId);
      toast.success('Rule deleted successfully!');
      loadData();
    } catch (error) {
      toast.error('Failed to delete rule');
    }
  };

  const getCategoryName = (categoryId) => {
    const cat = categories.find((c) => c.id === categoryId);
    return cat ? cat.name : 'Unknown';
  };

  const handleExport = async () => {
    try {
      const response = await exportRules();
      const rulesData = response.data;
      
      // Create JSON file
      const dataStr = JSON.stringify(rulesData, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      
      // Download file
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `categorization-rules-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      toast.success(`Exported ${rulesData.length} rules successfully!`);
    } catch (error) {
      toast.error('Failed to export rules');
    }
  };

  const handleImport = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      const text = await file.text();
      const rulesData = JSON.parse(text);
      
      if (!Array.isArray(rulesData)) {
        toast.error('Invalid file format. Expected an array of rules.');
        return;
      }

      const response = await importRules(rulesData);
      const { imported_count, skipped_count, message } = response.data;
      
      if (imported_count > 0) {
        toast.success(message);
        loadData();
      } else {
        toast.warning(message);
      }
    } catch (error) {
      if (error.message.includes('JSON')) {
        toast.error('Invalid JSON file');
      } else {
        toast.error('Failed to import rules');
      }
    } finally {
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading rules...</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8 md:px-8 md:py-12" data-testid="rules-page">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-2">Categorization Rules</h1>
          <p className="text-muted-foreground">Automate transaction categorization with custom rules</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleExport} disabled={rules.length === 0}>
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
          <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
            <Upload className="w-4 h-4 mr-2" />
            Import
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            onChange={handleImport}
            className="hidden"
          />
          <Dialog open={dialogOpen} onOpenChange={handleDialogChange}>
            <DialogTrigger asChild>
              <Button data-testid="add-rule-button">
                <Plus className="w-4 h-4 mr-2" />
                Add Rule
              </Button>
            </DialogTrigger>
            <DialogContent data-testid="add-rule-dialog">
            <DialogHeader>
              <DialogTitle>{editMode ? 'Edit Rule' : 'Create New Rule'}</DialogTitle>
              <DialogDescription>
                {editMode ? 'Update the pattern to automatically categorize transactions' : 'Define a pattern to automatically categorize transactions'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="pattern">Pattern</Label>
                <Input
                  id="pattern"
                  placeholder="e.g., ZOMATO, UPI-*, AMZN"
                  value={formData.pattern}
                  onChange={(e) => setFormData({ ...formData, pattern: e.target.value })}
                  required
                  data-testid="pattern-input"
                />
                <p className="text-xs text-muted-foreground">
                  Enter text to match in transaction descriptions
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="match-type">Match Type</Label>
                <Select
                  value={formData.match_type}
                  onValueChange={(value) => setFormData({ ...formData, match_type: value })}
                >
                  <SelectTrigger data-testid="match-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CONTAINS">Contains</SelectItem>
                    <SelectItem value="STARTS_WITH">Starts With</SelectItem>
                    <SelectItem value="ENDS_WITH">Ends With</SelectItem>
                    <SelectItem value="REGEX">Regex</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="category">Category</Label>
                <Select
                  value={formData.category_id}
                  onValueChange={(value) => setFormData({ ...formData, category_id: value })}
                >
                  <SelectTrigger data-testid="category-select">
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((category) => (
                      <SelectItem key={category.id} value={category.id}>
                        {category.name} ({category.type})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="priority">Priority (Higher = Applied First)</Label>
                <Input
                  id="priority"
                  type="number"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                  required
                  data-testid="priority-input"
                />
              </div>
              <Button type="submit" className="w-full" data-testid="submit-rule-button">
                Create Rule
              </Button>
            </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {rules.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Sparkles className="w-16 h-16 text-muted-foreground opacity-30 mb-4" />
            <p className="text-lg font-medium mb-2">No rules yet</p>
            <p className="text-sm text-muted-foreground mb-4">Create your first rule to automate categorization</p>
            <Button onClick={() => setDialogOpen(true)}>Create Rule</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {rules.map((rule) => (
            <Card key={rule.id} className="hover:shadow-md transition-shadow" data-testid={`rule-card-${rule.id}`}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <CardTitle className="text-xl">{rule.pattern}</CardTitle>
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                        {rule.match_type}
                      </span>
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-secondary">
                        Priority: {rule.priority}
                      </span>
                    </div>
                    <CardDescription>
                      Auto-categorize as: <span className="font-semibold">{getCategoryName(rule.category_id)}</span>
                    </CardDescription>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDelete(rule.id)}
                    data-testid={`delete-rule-${rule.id}`}
                  >
                    <Trash2 className="w-4 h-4 text-destructive" />
                  </Button>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default RulesPage;
