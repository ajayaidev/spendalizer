import React, { useState, useEffect } from 'react';
import { getAccounts, createAccount } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Wallet, CreditCard } from 'lucide-react';
import { toast } from 'sonner';

const AccountsPage = () => {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    account_type: 'BANK',
    institution: '',
    last_four: ''
  });

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const response = await getAccounts();
      setAccounts(response.data);
    } catch (error) {
      toast.error('Failed to load accounts');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await createAccount(formData);
      toast.success('Account created successfully!');
      setDialogOpen(false);
      setFormData({ name: '', account_type: 'BANK', institution: '', last_four: '' });
      loadAccounts();
    } catch (error) {
      toast.error('Failed to create account');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading accounts...</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8 md:px-8 md:py-12" data-testid="accounts-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-2">Accounts</h1>
          <p className="text-muted-foreground">Manage your bank accounts and credit cards</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="add-account-button">
              <Plus className="w-4 h-4 mr-2" />
              Add Account
            </Button>
          </DialogTrigger>
          <DialogContent data-testid="add-account-dialog">
            <DialogHeader>
              <DialogTitle>Add New Account</DialogTitle>
              <DialogDescription>Enter your account details below</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Account Name</Label>
                <Input
                  id="name"
                  placeholder="e.g., HDFC Savings"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  data-testid="account-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="account-type">Account Type</Label>
                <Select
                  value={formData.account_type}
                  onValueChange={(value) => setFormData({ ...formData, account_type: value })}
                >
                  <SelectTrigger data-testid="account-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="BANK">Bank Account</SelectItem>
                    <SelectItem value="CREDIT_CARD">Credit Card</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="institution">Institution</Label>
                <Input
                  id="institution"
                  placeholder="e.g., HDFC Bank"
                  value={formData.institution}
                  onChange={(e) => setFormData({ ...formData, institution: e.target.value })}
                  required
                  data-testid="institution-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="last-four">Last 4 Digits (Optional)</Label>
                <Input
                  id="last-four"
                  placeholder="1234"
                  maxLength={4}
                  value={formData.last_four}
                  onChange={(e) => setFormData({ ...formData, last_four: e.target.value })}
                  data-testid="last-four-input"
                />
              </div>
              <Button type="submit" className="w-full" data-testid="submit-account-button">
                Add Account
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {accounts.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Wallet className="w-16 h-16 text-muted-foreground opacity-30 mb-4" />
            <p className="text-lg font-medium mb-2">No accounts yet</p>
            <p className="text-sm text-muted-foreground mb-4">Add your first account to get started</p>
            <Button onClick={() => setDialogOpen(true)}>Add Account</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {accounts.map((account) => (
            <Card key={account.id} className="hover:shadow-lg transition-shadow" data-testid={`account-card-${account.id}`}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-xl mb-2">{account.name}</CardTitle>
                    <p className="text-sm text-muted-foreground">{account.institution}</p>
                    {account.last_four && (
                      <p className="text-xs text-muted-foreground mt-2">****{account.last_four}</p>
                    )}
                  </div>
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                    {account.account_type === 'BANK' ? (
                      <Wallet className="w-6 h-6 text-primary" />
                    ) : (
                      <CreditCard className="w-6 h-6 text-primary" />
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    account.account_type === 'BANK'
                      ? 'bg-blue-500/10 text-blue-700'
                      : 'bg-purple-500/10 text-purple-700'
                  }`}>
                    {account.account_type === 'BANK' ? 'Bank Account' : 'Credit Card'}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default AccountsPage;
