import React, { useState, useEffect } from 'react';
import { getCategories, createCategory, updateCategory, deleteCategory } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Trash2, Tag, Edit2 } from 'lucide-react';
import { toast } from 'sonner';

const CategoriesPage = () => {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    type: 'EXPENSE',
    parent_category_id: '_none'
  });

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      const response = await getCategories();
      // Sort categories alphabetically by name
      const sorted = response.data.sort((a, b) => {
        return a.name.localeCompare(b.name, 'en', { sensitivity: 'base' });
      });
      setCategories(sorted);
    } catch (error) {
      toast.error('Failed to load categories');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = {
        name: formData.name,
        type: formData.type,
        parent_category_id: formData.parent_category_id === '_none' ? null : formData.parent_category_id
      };
      
      if (editingCategory) {
        await updateCategory(editingCategory.id, data);
        toast.success('Category updated successfully!');
      } else {
        await createCategory(data);
        toast.success('Category created successfully!');
      }
      
      setDialogOpen(false);
      setEditingCategory(null);
      setFormData({ name: '', type: 'EXPENSE', parent_category_id: '_none' });
      loadCategories();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${editingCategory ? 'update' : 'create'} category`);
    }
  };

  const handleEdit = (category) => {
    setEditingCategory(category);
    setFormData({
      name: category.name,
      type: category.type,
      parent_category_id: category.parent_category_id || '_none'
    });
    setDialogOpen(true);
  };

  const handleDelete = async (categoryId) => {
    if (!window.confirm('Are you sure you want to delete this category?')) return;
    
    try {
      await deleteCategory(categoryId);
      toast.success('Category deleted successfully!');
      loadCategories();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete category');
    }
  };

  const groupedCategories = {
    INCOME: categories.filter(c => c.type === 'INCOME'),
    EXPENSE: categories.filter(c => c.type === 'EXPENSE'),
    TRANSFER: categories.filter(c => c.type === 'TRANSFER')
  };

  const parentCategories = categories.filter(c => !c.parent_category_id);

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading categories...</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8 md:px-8 md:py-12" data-testid="categories-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-2">Categories</h1>
          <p className="text-muted-foreground">Manage your transaction categories and sub-categories</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) {
            setEditingCategory(null);
            setFormData({ name: '', type: 'EXPENSE', parent_category_id: '_none' });
          }
        }}>
          <DialogTrigger asChild>
            <Button data-testid="add-category-button">
              <Plus className="w-4 h-4 mr-2" />
              Add Category
            </Button>
          </DialogTrigger>
          <DialogContent data-testid="add-category-dialog">
            <DialogHeader>
              <DialogTitle>{editingCategory ? 'Edit Category' : 'Create New Category'}</DialogTitle>
              <DialogDescription>
                {editingCategory ? 'Update category details' : 'Add a custom category or sub-category'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Category Name</Label>
                <Input
                  id="name"
                  placeholder="e.g., Coffee Shops"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  data-testid="category-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="type">Type</Label>
                <Select
                  value={formData.type}
                  onValueChange={(value) => setFormData({ ...formData, type: value })}
                >
                  <SelectTrigger data-testid="category-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="INCOME">Income</SelectItem>
                    <SelectItem value="EXPENSE">Expense</SelectItem>
                    <SelectItem value="TRANSFER">Transfer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="parent">Parent Category (Optional)</Label>
                <Select
                  value={formData.parent_category_id}
                  onValueChange={(value) => setFormData({ ...formData, parent_category_id: value })}
                >
                  <SelectTrigger data-testid="parent-category-select">
                    <SelectValue placeholder="None (Top-level category)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_none">None (Top-level category)</SelectItem>
                    {parentCategories
                      .filter(c => c.type === formData.type && c.id && c.id.trim() !== '')
                      .map((cat) => (
                        <SelectItem key={cat.id} value={cat.id}>
                          {cat.name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
              <Button type="submit" className="w-full" data-testid="submit-category-button">
                {editingCategory ? 'Update Category' : 'Create Category'}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Category Groups */}
      <div className="space-y-8">
        {Object.entries(groupedCategories).map(([type, cats]) => (
          <Card key={type}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Tag className="w-5 h-5" />
                {type === 'INCOME' ? 'Income Categories' : 
                 type === 'EXPENSE' ? 'Expense Categories' : 
                 'Transfer Categories'}
              </CardTitle>
              <CardDescription>
                {cats.length} {cats.length === 1 ? 'category' : 'categories'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {cats.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4">No custom categories yet</p>
              ) : (
                <div className="space-y-2">
                  {cats.map((category) => (
                    <div
                      key={category.id}
                      className="flex items-center justify-between p-3 rounded-lg border hover:bg-secondary transition-colors"
                      data-testid={`category-${category.id}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          category.type === 'INCOME' ? 'bg-green-500/10' :
                          category.type === 'EXPENSE' ? 'bg-red-500/10' :
                          'bg-blue-500/10'
                        }`}>
                          <Tag className={`w-5 h-5 ${
                            category.type === 'INCOME' ? 'text-green-600' :
                            category.type === 'EXPENSE' ? 'text-red-600' :
                            'text-blue-600'
                          }`} />
                        </div>
                        <div>
                          <p className="font-medium">{category.name}</p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            {category.is_system ? (
                              <span className="px-2 py-0.5 rounded-full bg-secondary">System</span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary">Custom</span>
                            )}
                            {category.parent_category_id && (
                              <span>Sub-category</span>
                            )}
                          </div>
                        </div>
                      </div>
                      {category.is_system !== true && (
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(category)}
                            data-testid={`edit-category-${category.id}`}
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(category.id)}
                            data-testid={`delete-category-${category.id}`}
                          >
                            <Trash2 className="w-4 h-4 text-destructive" />
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default CategoriesPage;
