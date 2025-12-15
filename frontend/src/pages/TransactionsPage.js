import React, { useState, useEffect } from 'react';
import { getTransactions, getCategories, getAccounts, updateTransactionCategory, createCategory, bulkCategorizeTransactions, bulkCategorizeByRules, bulkCategorizeByAI, createRule } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Calendar } from '../components/ui/calendar';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '../components/ui/command';
import { Checkbox } from '../components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Search, Filter, Calendar as CalendarIcon, Check, ChevronsUpDown, Plus, Tag, Sparkles, Brain } from 'lucide-react';
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
  const [newCategory, setNewCategory] = useState('_none');
  const [categorySearch, setCategorySearch] = useState('');
  const [categoryComboOpen, setCategoryComboOpen] = useState(false);
  const [showNewCategoryDialog, setShowNewCategoryDialog] = useState(false);
  const [newCategoryForm, setNewCategoryForm] = useState({ name: '', type: 'EXPENSE' });
  
  // Create rule after categorization states
  const [showCreateRuleDialog, setShowCreateRuleDialog] = useState(false);
  const [ruleTransaction, setRuleTransaction] = useState(null);
  const [ruleForm, setRuleForm] = useState({ pattern: '', match_type: 'CONTAINS', priority: 10 });
  
  // Bulk categorization states
  const [selectedTransactions, setSelectedTransactions] = useState([]);
  const [showBulkDialog, setShowBulkDialog] = useState(false);
  const [bulkCategory, setBulkCategory] = useState('');
  const [bulkCategorySearch, setBulkCategorySearch] = useState('');
  const [bulkComboOpen, setBulkComboOpen] = useState(false);
  const [bulkMethod, setBulkMethod] = useState('manual');
  const [bulkLoading, setBulkLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [selectedAccount, selectedCategory, dateRange]);

  const loadData = async () => {
    try {
      const params = {};
      if (selectedAccount && selectedAccount !== '_all') params.account_id = selectedAccount;
      if (selectedCategory && selectedCategory === '_uncategorized') {
        params.uncategorized = 'true';
      } else if (selectedCategory && selectedCategory !== '_all') {
        params.category_id = selectedCategory;
      }
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
    if (!newCategory || newCategory === '_none' || !editingTxn) return;
    
    try {
      await updateTransactionCategory(editingTxn.id, newCategory);
      toast.success('Category updated successfully!');
      
      // Store transaction info for rule creation prompt
      const txn = editingTxn;
      const selectedCategoryId = newCategory;
      
      setEditingTxn(null);
      setNewCategory('_none');
      await loadData();
      
      // Prompt user to create a rule
      setRuleTransaction({ ...txn, category_id: selectedCategoryId });
      setRuleForm({ 
        pattern: txn.description || '', 
        match_type: 'CONTAINS', 
        priority: 10 
      });
      setShowCreateRuleDialog(true);
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

  const handleCreateRule = async () => {
    if (!ruleForm.pattern || !ruleTransaction?.category_id) {
      toast.error('Pattern and category are required');
      return;
    }

    try {
      await createRule({
        pattern: ruleForm.pattern,
        match_type: ruleForm.match_type,
        category_id: ruleTransaction.category_id,
        priority: ruleForm.priority
      });
      toast.success('Rule created successfully! Future similar transactions will be categorized automatically.');
      setShowCreateRuleDialog(false);
      setRuleTransaction(null);
      setRuleForm({ pattern: '', match_type: 'CONTAINS', priority: 10 });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create rule');
    }
  };

  const handleSkipRuleCreation = () => {
    setShowCreateRuleDialog(false);
    setRuleTransaction(null);
    setRuleForm({ pattern: '', match_type: 'CONTAINS', priority: 10 });
  };

  const handleBulkCategorize = async () => {
    if (selectedTransactions.length === 0) {
      toast.error('Please select transactions');
      return;
    }

    if (bulkMethod === 'manual' && !bulkCategory) {
      toast.error('Please select a category');
      return;
    }

    setBulkLoading(true);
    try {
      let response;
      
      if (bulkMethod === 'manual') {
        response = await bulkCategorizeTransactions(selectedTransactions, bulkCategory);
        toast.success(`Successfully categorized ${response.data.updated_count} transactions!`);
      } else if (bulkMethod === 'rules') {
        response = await bulkCategorizeByRules(selectedTransactions);
        const data = response.data;
        if (data.updated_count === 0) {
          toast.warning(data.message || `No transactions matched your rules. ${data.rules_available || 0} rules available.`);
        } else {
          toast.success(`Successfully categorized ${data.updated_count} of ${selectedTransactions.length} transactions using rules!`);
        }
      } else if (bulkMethod === 'ai') {
        response = await bulkCategorizeByAI(selectedTransactions);
        const data = response.data;
        if (data.updated_count === 0) {
          toast.warning('No transactions were categorized by AI. Ensure Ollama is running locally.');
        } else {
          toast.success(`AI categorized ${data.updated_count} of ${selectedTransactions.length} transactions!`);
        }
      }
      
      setShowBulkDialog(false);
      setBulkCategory('');
      setBulkMethod('manual');
      setSelectedTransactions([]);
      loadData();
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to bulk categorize transactions';
      toast.error(errorMsg);
    } finally {
      setBulkLoading(false);
    }
  };

  const toggleTransactionSelection = (txnId) => {
    setSelectedTransactions(prev =>
      prev.includes(txnId)
        ? prev.filter(id => id !== txnId)
        : [...prev, txnId]
    );
  };

  const selectAllTransactions = () => {
    if (selectedTransactions.length === filteredTransactions.length) {
      setSelectedTransactions([]);
    } else {
      setSelectedTransactions(filteredTransactions.map(t => t.id));
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
                {accounts.filter(acc => acc.id && acc.id.trim() !== '').map((account) => (
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
                <SelectItem value="_uncategorized">Uncategorized</SelectItem>
                {categories.filter(cat => cat.id && cat.id.trim() !== '').map((category) => (
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
          <div className="flex items-center justify-between">
            <CardTitle>All Transactions ({filteredTransactions.length})</CardTitle>
            {selectedTransactions.length > 0 && (
              <Button onClick={() => setShowBulkDialog(true)} size="sm">
                <Tag className="w-4 h-4 mr-2" />
                Categorize Selected ({selectedTransactions.length})
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {filteredTransactions.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <p>No transactions found</p>
            </div>
          ) : (
            <>
              {filteredTransactions.length > 0 && (
                <div className="flex items-center gap-2 mb-4 pb-3 border-b">
                  <Checkbox
                    checked={selectedTransactions.length === filteredTransactions.length}
                    onCheckedChange={selectAllTransactions}
                    id="select-all"
                  />
                  <Label htmlFor="select-all" className="text-sm font-medium cursor-pointer">
                    Select All ({filteredTransactions.length})
                  </Label>
                </div>
              )}
              <div className="space-y-3">
                {filteredTransactions.map((txn) => (
                  <div
                    key={txn.id}
                    className="flex items-center gap-3 p-4 rounded-lg border hover:bg-secondary transition-colors"
                    data-testid={`transaction-row-${txn.id}`}
                  >
                    <Checkbox
                      checked={selectedTransactions.includes(txn.id)}
                      onCheckedChange={() => toggleTransactionSelection(txn.id)}
                      id={`txn-${txn.id}`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <p className="font-medium truncate">{txn.description}</p>
                      <span
                        className="px-2 py-1 rounded-full text-xs font-medium bg-secondary cursor-pointer hover:bg-primary/10"
                        onClick={() => {
                          setEditingTxn(txn);
                          setNewCategory(txn.category_id || '_none');
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
            </>
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
                      {newCategory && newCategory !== '_none'
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
                  <SelectItem value="INCOME">1. Income</SelectItem>
                  <SelectItem value="EXPENSE">2. Expense</SelectItem>
                  <SelectItem value="TRANSFER_EXTERNAL_IN">3. External Transfer IN (Investment Returns)</SelectItem>
                  <SelectItem value="TRANSFER_EXTERNAL_OUT">4. External Transfer OUT (Investments, Loans)</SelectItem>
                  <SelectItem value="TRANSFER_INTERNAL_IN">5. Internal Transfer IN (Bank Deposits)</SelectItem>
                  <SelectItem value="TRANSFER_INTERNAL_OUT">6. Internal Transfer OUT (Bank Withdrawals)</SelectItem>
                  <SelectItem value="TRANSFER">7. Transfer (Legacy)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleCreateNewCategory} className="w-full">
              Create and Use Category
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Bulk Categorize Dialog */}
      <Dialog open={showBulkDialog} onOpenChange={(open) => {
        setShowBulkDialog(open);
        if (!open) {
          setBulkCategory('');
          setBulkCategorySearch('');
          setBulkMethod('manual');
        }
      }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Bulk Categorize Transactions</DialogTitle>
            <DialogDescription>
              Categorize {selectedTransactions.length} selected transaction{selectedTransactions.length !== 1 ? 's' : ''}
            </DialogDescription>
          </DialogHeader>
          
          <Tabs value={bulkMethod} onValueChange={setBulkMethod} className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="manual">
                <Tag className="w-4 h-4 mr-2" />
                Manual
              </TabsTrigger>
              <TabsTrigger value="rules">
                <Sparkles className="w-4 h-4 mr-2" />
                Rules
              </TabsTrigger>
              <TabsTrigger value="ai">
                <Brain className="w-4 h-4 mr-2" />
                AI
              </TabsTrigger>
            </TabsList>

            <TabsContent value="manual" className="space-y-4">
              <div className="space-y-2">
                <Label>Select Category</Label>
                <Popover open={bulkComboOpen} onOpenChange={setBulkComboOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={bulkComboOpen}
                      className="w-full justify-between"
                    >
                      {bulkCategory
                        ? categories.find((cat) => cat.id === bulkCategory)?.name
                        : "Select category..."}
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-full p-0">
                    <Command>
                      <CommandInput
                        placeholder="Search categories..."
                        value={bulkCategorySearch}
                        onValueChange={setBulkCategorySearch}
                      />
                      <CommandList>
                        <CommandEmpty>No category found.</CommandEmpty>
                        
                        {/* Income Categories */}
                        {categories.filter(c => c.type === 'INCOME' && c.name.toLowerCase().includes(bulkCategorySearch.toLowerCase())).length > 0 && (
                          <CommandGroup heading="Income">
                            {categories
                              .filter(c => c.type === 'INCOME' && c.name.toLowerCase().includes(bulkCategorySearch.toLowerCase()))
                              .map((category) => (
                                <CommandItem
                                  key={category.id}
                                  value={category.id}
                                  onSelect={() => {
                                    setBulkCategory(category.id);
                                    setBulkComboOpen(false);
                                  }}
                                >
                                  <Check
                                    className={cn(
                                      "mr-2 h-4 w-4",
                                      bulkCategory === category.id ? "opacity-100" : "opacity-0"
                                    )}
                                  />
                                  {category.name}
                                </CommandItem>
                              ))}
                          </CommandGroup>
                        )}
                        
                        {/* Expense Categories */}
                        {categories.filter(c => c.type === 'EXPENSE' && c.name.toLowerCase().includes(bulkCategorySearch.toLowerCase())).length > 0 && (
                          <CommandGroup heading="Expense">
                            {categories
                              .filter(c => c.type === 'EXPENSE' && c.name.toLowerCase().includes(bulkCategorySearch.toLowerCase()))
                              .map((category) => (
                                <CommandItem
                                  key={category.id}
                                  value={category.id}
                                  onSelect={() => {
                                    setBulkCategory(category.id);
                                    setBulkComboOpen(false);
                                  }}
                                >
                                  <Check
                                    className={cn(
                                      "mr-2 h-4 w-4",
                                      bulkCategory === category.id ? "opacity-100" : "opacity-0"
                                    )}
                                  />
                                  {category.name}
                                </CommandItem>
                              ))}
                          </CommandGroup>
                        )}
                        
                        {/* Transfer Categories */}
                        {categories.filter(c => c.type?.startsWith('TRANSFER') && c.name.toLowerCase().includes(bulkCategorySearch.toLowerCase())).length > 0 && (
                          <CommandGroup heading="Transfers">
                            {categories
                              .filter(c => c.type?.startsWith('TRANSFER') && c.name.toLowerCase().includes(bulkCategorySearch.toLowerCase()))
                              .map((category) => (
                                <CommandItem
                                  key={category.id}
                                  value={category.id}
                                  onSelect={() => {
                                    setBulkCategory(category.id);
                                    setBulkComboOpen(false);
                                  }}
                                >
                                  <Check
                                    className={cn(
                                      "mr-2 h-4 w-4",
                                      bulkCategory === category.id ? "opacity-100" : "opacity-0"
                                    )}
                                  />
                                  {category.name} ({category.type.replace('TRANSFER_', '').replace('_', ' ')})
                                </CommandItem>
                              ))}
                          </CommandGroup>
                        )}
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
                <p className="text-sm text-muted-foreground">
                  Manually assign a category to all selected transactions
                </p>
              </div>
            </TabsContent>

            <TabsContent value="rules" className="space-y-4">
              <div className="rounded-lg border p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-primary" />
                  <h4 className="font-medium">Rule-based Categorization</h4>
                </div>
                <p className="text-sm text-muted-foreground">
                  Automatically categorize transactions based on your existing rules. Rules are applied in priority order, matching transaction descriptions against patterns.
                </p>
                <p className="text-sm font-medium text-muted-foreground mt-2">
                  ✓ Fast and deterministic<br/>
                  ✓ Uses your custom rules<br/>
                  ✓ No external API calls
                </p>
              </div>
            </TabsContent>

            <TabsContent value="ai" className="space-y-4">
              <div className="rounded-lg border p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <Brain className="w-5 h-5 text-primary" />
                  <h4 className="font-medium">AI-Powered Categorization</h4>
                </div>
                <p className="text-sm text-muted-foreground">
                  Use local LLM (Ollama) to intelligently categorize transactions based on description context and your existing categories.
                </p>
                <p className="text-sm font-medium text-muted-foreground mt-2">
                  ✓ Context-aware<br/>
                  ✓ Learns from categories<br/>
                  ✓ Handles complex descriptions
                </p>
                <p className="text-xs text-amber-600 mt-2">
                  Note: Requires Ollama running locally
                </p>
              </div>
            </TabsContent>
          </Tabs>

          <div className="flex gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setShowBulkDialog(false);
                setBulkCategory('');
                setBulkMethod('manual');
              }}
              disabled={bulkLoading}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handleBulkCategorize}
              disabled={(bulkMethod === 'manual' && !bulkCategory) || bulkLoading}
              className="flex-1"
            >
              {bulkLoading ? 'Processing...' : `Categorize ${selectedTransactions.length}`}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Create Rule Dialog */}
      <Dialog open={showCreateRuleDialog} onOpenChange={setShowCreateRuleDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Tag className="w-5 h-5" />
              Create Rule for Auto-Categorization?
            </DialogTitle>
            <DialogDescription>
              Want to automatically categorize similar transactions in the future?
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
              <p className="text-sm font-medium text-blue-900">Transaction Details:</p>
              <p className="text-sm text-blue-800 mt-1">
                <span className="font-medium">Description:</span> {ruleTransaction?.description}
              </p>
              <p className="text-sm text-blue-800">
                <span className="font-medium">Amount:</span> ₹{ruleTransaction?.amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="rule-pattern">Pattern to Match</Label>
              <Input
                id="rule-pattern"
                value={ruleForm.pattern}
                onChange={(e) => setRuleForm({ ...ruleForm, pattern: e.target.value })}
                placeholder="e.g., ZOMATO, UPI-, SALARY"
              />
              <p className="text-xs text-muted-foreground">
                Edit to match similar transactions (e.g., "ZOMATO" will match all Zomato orders)
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="rule-match-type">Match Type</Label>
              <Select 
                value={ruleForm.match_type} 
                onValueChange={(value) => setRuleForm({ ...ruleForm, match_type: value })}
              >
                <SelectTrigger id="rule-match-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CONTAINS">Contains</SelectItem>
                  <SelectItem value="STARTS_WITH">Starts With</SelectItem>
                  <SelectItem value="ENDS_WITH">Ends With</SelectItem>
                  <SelectItem value="EXACT">Exact Match</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="rule-priority">Priority (1-100)</Label>
              <Input
                id="rule-priority"
                type="number"
                min="1"
                max="100"
                value={ruleForm.priority}
                onChange={(e) => setRuleForm({ ...ruleForm, priority: parseInt(e.target.value) || 10 })}
              />
              <p className="text-xs text-muted-foreground">
                Higher priority rules are applied first
              </p>
            </div>

            <div className="p-3 rounded-lg bg-green-50 border border-green-200">
              <p className="text-sm text-green-900">
                ✓ Future transactions matching this pattern will be automatically categorized
              </p>
            </div>

            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={handleSkipRuleCreation}
                className="flex-1"
              >
                Skip
              </Button>
              <Button
                onClick={handleCreateRule}
                className="flex-1"
              >
                <Tag className="w-4 h-4 mr-2" />
                Create Rule
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TransactionsPage;
