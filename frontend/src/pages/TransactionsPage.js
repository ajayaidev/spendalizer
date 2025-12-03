import React, { useState, useEffect } from 'react';
import { getTransactions, getCategories, getAccounts, updateTransactionCategory } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Search, Filter } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const TransactionsPage = () => {
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAccount, setSelectedAccount] = useState('_all');
  const [selectedCategory, setSelectedCategory] = useState('_all');
  const [editingTxn, setEditingTxn] = useState(null);
  const [newCategory, setNewCategory] = useState('');

  useEffect(() => {
    loadData();
  }, [selectedAccount, selectedCategory]);

  const loadData = async () => {
    try {
      const params = {};
      if (selectedAccount && selectedAccount !== '_all') params.account_id = selectedAccount;
      if (selectedCategory && selectedCategory !== '_all') params.category_id = selectedCategory;
      
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
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
            <Button
              variant="outline"
              onClick={() => {
                setSearchTerm('');
                setSelectedAccount('_all');
                setSelectedCategory('_all');
              }}
              data-testid="clear-filters-button"
            >
              <Filter className="w-4 h-4 mr-2" />
              Clear Filters
            </Button>
          </div>
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

      {/* Edit Category Dialog */}
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
                <Select value={newCategory} onValueChange={setNewCategory}>
                  <SelectTrigger data-testid="new-category-select">
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((category) => (
                      <SelectItem key={category.id} value={category.id}>
                        {category.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={handleCategoryUpdate} className="w-full" data-testid="update-category-button">
                Update Category
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TransactionsPage;
