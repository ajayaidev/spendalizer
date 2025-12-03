import React, { useState, useEffect } from 'react';
import { getRules, createRule, deleteRule, getCategories } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Trash2, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

const RulesPage = () => {
  const [rules, setRules] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    pattern: '',
    match_type: 'CONTAINS',
    category_id: '',
    priority: 10
  });

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
      await createRule(formData);
      toast.success('Rule created successfully!');
      setDialogOpen(false);
      setFormData({ pattern: '', match_type: 'CONTAINS', category_id: '', priority: 10 });
      loadData();
    } catch (error) {
      toast.error('Failed to create rule');
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

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading rules...</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8 md:px-8 md:py-12" data-testid="rules-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-2">Categorization Rules</h1>
          <p className="text-muted-foreground">Automate transaction categorization with custom rules</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="add-rule-button">
              <Plus className="w-4 h-4 mr-2" />
              Add Rule
            </Button>
          </DialogTrigger>
          <DialogContent data-testid="add-rule-dialog">
            <DialogHeader>
              <DialogTitle>Create New Rule</DialogTitle>
              <DialogDescription>Define a pattern to automatically categorize transactions</DialogDescription>
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
