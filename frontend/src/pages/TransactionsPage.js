import React, { useState, useEffect } from 'react';
import { getTransactions, getCategories, getAccounts, updateTransactionCategory, createCategory } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Calendar } from '../components/ui/calendar';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '../components/ui/command';
import { Search, Filter, Calendar as CalendarIcon, Check, ChevronsUpDown, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { format, subMonths, startOfMonth, endOfMonth, startOfYear, endOfYear } from 'date-fns';
import { cn } from '../lib/utils';

const TransactionsPage = () => {
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAccount, setSelectedAccount] = useState('_all');
  const [selectedCategory, setSelectedCategory] = useState('_all');
  const [dateRange, setDateRange] = useState({ from: null, to: null });
  const [editingTxn, setEditingTxn] = useState(null);
  const [newCategory, setNewCategory] = useState('');
  const [categorySearch, setCategorySearch] = useState('');
  const [categoryComboOpen, setCategoryComboOpen] = useState(false);
  const [showNewCategoryDialog, setShowNewCategoryDialog] = useState(false);
  const [newCategoryForm, setNewCategoryForm] = useState({ name: '', type: 'EXPENSE' });

  useEffect(() => {
    loadData();
  }, [selectedAccount, selectedCategory, dateRange]);

  const loadData = async () => {
    try {
      const params = {};
      if (selectedAccount && selectedAccount !== '_all') params.account_id = selectedAccount;
      if (selectedCategory && selectedCategory !== '_all') params.category_id = selectedCategory;
      if (dateRange.from) params.start_date = format(dateRange.from, 'yyyy-MM-dd');
      if (dateRange.to) params.end_date = format(dateRange.to, 'yyyy-MM-dd');
      
      const [txnRes, catRes, accRes] = await Promise.all([
        getTransactions(params),
        getCategories(),
        getAccounts()
      ]);
      
      setTransactions(txnRes.data.transactions);
      setCategories(catRes.data);
      setAccounts(accRes.data);
    } catch (error) {
      toast.error('Failed to load transactions');
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryUpdate = async () => {
    if (!newCategory || !editingTxn) return;
    
    try {
      await updateTransactionCategory(editingTxn.id, newCategory);
      toast.success('Category updated successfully!');
      setEditingTxn(null);
      setNewCategory('');
      loadData();
    } catch (error) {
      toast.error('Failed to update category');
    }
  };

  const handleCreateNewCategory = async () => {
    try {
      const response = await createCategory(newCategoryForm);
      toast.success('Category created successfully!');
      setShowNewCategoryDialog(false);
      setNewCategoryForm({ name: '', type: 'EXPENSE' });
      await loadData();
      // Auto-select the newly created category
      setNewCategory(response.data.id);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create category');
    }
  };

  const setDatePreset = (preset) => {
    const today = new Date();
    switch (preset) {
      case 'this-month':
        setDateRange({ from: startOfMonth(today), to: endOfMonth(today) });
        break;
      case 'last-month':
        const lastMonth = subMonths(today, 1);
        setDateRange({ from: startOfMonth(lastMonth), to: endOfMonth(lastMonth) });
        break;
      case 'this-year':
        setDateRange({ from: startOfYear(today), to: endOfYear(today) });
        break;
      case 'last-3-months':
        setDateRange({ from: subMonths(today, 3), to: today });
        break;
      case 'last-6-months':
        setDateRange({ from: subMonths(today, 6), to: today });
        break;
      case 'clear':
        setDateRange({ from: null, to: null });
        break;
      default:
        break;
    }
  };

  const filteredTransactions = transactions.filter((txn) =>
    txn.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getCategoryName = (categoryId) => {
    const cat = categories.find((c) => c.id === categoryId);
    return cat ? cat.name : 'Uncategorized';
  };

  const getAccountName = (accountId) => {
    const acc = accounts.find((a) => a.id === accountId);
    return acc ? acc.name : 'Unknown';
  };

  const filteredCategories = categories.filter((cat) =>
    cat.name.toLowerCase().includes(categorySearch.toLowerCase())
  );

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading transactions...</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8 md:px-8 md:py-12" data-testid="transactions-page">
      <div className="mb-8">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-2">Transactions</h1>
        <p className="text-muted-foreground">View and manage all your transactions</p>
      </div>

      {/* Filters */}
      <Card className="mb-6" data-testid="filters-card">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search transactions..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
                data-testid="search-input"
              />
            </div>
            <Select value={selectedAccount} onValueChange={setSelectedAccount}>
              <SelectTrigger data-testid="account-filter-select">
                <SelectValue placeholder="All Accounts" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_all">All Accounts</SelectItem>
                {accounts.map((account) => (
                  <SelectItem key={account.id} value={account.id}>
                    {account.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger data-testid="category-filter-select">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_all">All Categories</SelectItem>
                {categories.map((category) => (
                  <SelectItem key={category.id} value={category.id}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="justify-start text-left font-normal">
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {dateRange.from ? (
                    dateRange.to ? (
                      <>
                        {format(dateRange.from, 'LLL dd, y')} - {format(dateRange.to, 'LLL dd, y')}
                      </>
                    ) : (
                      format(dateRange.from, 'LLL dd, y')
                    )
                  ) : (
                    <span>Pick date range</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <div className="p-3 border-b">
                  <div className="grid grid-cols-2 gap-2">
                    <Button size="sm" variant="outline" onClick={() => setDatePreset('this-month')}>
                      This Month
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setDatePreset('last-month')}>
                      Last Month
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setDatePreset('last-3-months')}>
                      Last 3 Months
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setDatePreset('last-6-months')}>
                      Last 6 Months
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setDatePreset('this-year')}>
                      This Year
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setDatePreset('clear')}>
                      Clear
                    </Button>
                  </div>
                </div>
                <Calendar
                  mode="range"
                  selected={dateRange}
                  onSelect={setDateRange}
                  numberOfMonths={2}
                />
              </PopoverContent>
            </Popover>
          </div>
          <Button
            variant="outline"
            onClick={() => {
              setSearchTerm('');
              setSelectedAccount('_all');
              setSelectedCategory('_all');
              setDateRange({ from: null, to: null });
            }}
            data-testid="clear-filters-button"
          >
            <Filter className="w-4 h-4 mr-2" />
            Clear All Filters
          </Button>
        </CardContent>
      </Card>

      {/* Transactions Table */}
      <Card data-testid="transactions-table-card">
        <CardHeader>
          <CardTitle>All Transactions ({filteredTransactions.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {filteredTransactions.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <p>No transactions found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredTransactions.map((txn) => (
                <div
                  key={txn.id}
                  className="flex items-center justify-between p-4 rounded-lg border hover:bg-secondary transition-colors"
                  data-testid={`transaction-row-${txn.id}`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <p className="font-medium truncate">{txn.description}</p>
                      <span
                        className="px-2 py-1 rounded-full text-xs font-medium bg-secondary cursor-pointer hover:bg-primary/10"
                        onClick={() => {
                          setEditingTxn(txn);
                          setNewCategory(txn.category_id || '');
                        }}
                        data-testid={`category-badge-${txn.id}`}
                      >
                        {getCategoryName(txn.category_id)}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>{format(new Date(txn.date), 'MMM dd, yyyy')}</span>
                      <span>•</span>
                      <span>{getAccountName(txn.account_id)}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div
                      className={`text-lg font-semibold ${
                        txn.direction === 'CREDIT' ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {txn.direction === 'CREDIT' ? '+' : '-'}₹{txn.amount.toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Category Dialog with Search */}
      <Dialog open={!!editingTxn} onOpenChange={(open) => !open && setEditingTxn(null)}>
        <DialogContent data-testid="edit-category-dialog">
          <DialogHeader>
            <DialogTitle>Update Category</DialogTitle>
            <DialogDescription>Change the category for this transaction</DialogDescription>
          </DialogHeader>
          {editingTxn && (
            <div className="space-y-4">
              <div>
                <p className="font-medium">{editingTxn.description}</p>
                <p className="text-sm text-muted-foreground">₹{editingTxn.amount.toLocaleString()}</p>
              </div>
              <div className="space-y-2">
                <Label>Category</Label>
                <Popover open={categoryComboOpen} onOpenChange={setCategoryComboOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={categoryComboOpen}
                      className="w-full justify-between"
                      data-testid="category-combobox-trigger"
                    >
                      {newCategory
                        ? categories.find((cat) => cat.id === newCategory)?.name
                        : 'Select category...'}
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[400px] p-0">
                    <Command>
                      <CommandInput
                        placeholder="Search category..."
                        value={categorySearch}
                        onValueChange={setCategorySearch}
                      />
                      <CommandList>
                        <CommandEmpty>
                          <div className="py-2">
                            <p className="text-sm text-muted-foreground mb-2">No category found.</p>
                            <Button
                              size="sm"
                              variant="outline"
                              className="w-full"
                              onClick={() => {
                                setShowNewCategoryDialog(true);
                                setCategoryComboOpen(false);
                              }}
                            >
                              <Plus className="w-4 h-4 mr-2" />
                              Create New Category
                            </Button>
                          </div>
                        </CommandEmpty>
                        <CommandGroup>
                          {filteredCategories.map((category) => (
                            <CommandItem
                              key={category.id}
                              value={category.name}
                              onSelect={() => {
                                setNewCategory(category.id);
                                setCategoryComboOpen(false);
                              }}
                            >
                              <Check
                                className={cn(
                                  'mr-2 h-4 w-4',
                                  newCategory === category.id ? 'opacity-100' : 'opacity-0'
                                )}
                              />
                              {category.name}
                              <span className="ml-auto text-xs text-muted-foreground">
                                {category.type}
                              </span>
                            </CommandItem>
                          ))}
                        </CommandGroup>
                        {filteredCategories.length > 0 && (
                          <div className="p-2 border-t">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="w-full justify-start"
                              onClick={() => {
                                setShowNewCategoryDialog(true);
                                setCategoryComboOpen(false);
                              }}
                            >
                              <Plus className="w-4 h-4 mr-2" />
                              Create New Category
                            </Button>
                          </div>
                        )}
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>
              <Button onClick={handleCategoryUpdate} className="w-full" data-testid="update-category-button">
                Update Category
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Create New Category Dialog */}
      <Dialog open={showNewCategoryDialog} onOpenChange={setShowNewCategoryDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Category</DialogTitle>
            <DialogDescription>Add a custom category for your transactions</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="new-cat-name">Category Name</Label>
              <Input
                id="new-cat-name"
                placeholder="e.g., Coffee Shops"
                value={newCategoryForm.name}
                onChange={(e) => setNewCategoryForm({ ...newCategoryForm, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-cat-type">Type</Label>
              <Select
                value={newCategoryForm.type}
                onValueChange={(value) => setNewCategoryForm({ ...newCategoryForm, type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="INCOME">Income</SelectItem>
                  <SelectItem value="EXPENSE">Expense</SelectItem>
                  <SelectItem value="TRANSFER">Transfer</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleCreateNewCategory} className="w-full">
              Create and Use Category
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TransactionsPage;
