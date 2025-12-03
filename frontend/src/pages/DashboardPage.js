import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getAnalyticsSummary, getTransactions, getAccounts } from '../lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { TrendingUp, TrendingDown, Wallet, Receipt } from 'lucide-react';
import { format } from 'date-fns';

const DashboardPage = () => {
  const [summary, setSummary] = useState(null);
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [summaryRes, txnRes, accountsRes] = await Promise.all([
        getAnalyticsSummary(),
        getTransactions({ limit: 10 }),
        getAccounts()
      ]);
      setSummary(summaryRes.data);
      setRecentTransactions(txnRes.data.transactions);
      setAccounts(accountsRes.data);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 md:px-8 md:py-12" data-testid="dashboard-page">
      <div className="mb-8">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-2">Dashboard</h1>
        <p className="text-muted-foreground">Your financial overview at a glance</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <Card data-testid="income-card">
          <CardHeader className="pb-3">
            <CardDescription className="text-xs uppercase tracking-wide">Total Income</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-3xl font-bold">₹{summary?.total_income?.toLocaleString() || '0'}</div>
              </div>
              <div className="w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="expense-card">
          <CardHeader className="pb-3">
            <CardDescription className="text-xs uppercase tracking-wide">Total Expense</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-3xl font-bold">₹{summary?.total_expense?.toLocaleString() || '0'}</div>
              </div>
              <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center">
                <TrendingDown className="w-6 h-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="savings-card">
          <CardHeader className="pb-3">
            <CardDescription className="text-xs uppercase tracking-wide">Net Savings</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-3xl font-bold">₹{summary?.net_savings?.toLocaleString() || '0'}</div>
              </div>
              <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center">
                <Wallet className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="transactions-card">
          <CardHeader className="pb-3">
            <CardDescription className="text-xs uppercase tracking-wide">Transactions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-3xl font-bold">{summary?.transaction_count || 0}</div>
              </div>
              <div className="w-12 h-12 rounded-full bg-purple-500/10 flex items-center justify-center">
                <Receipt className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Transactions & Accounts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2" data-testid="recent-transactions-card">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Recent Transactions</CardTitle>
              <Link to="/transactions" className="text-sm text-primary hover:underline" data-testid="view-all-transactions-link">
                View all
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {recentTransactions.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Receipt className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>No transactions yet</p>
                <Link to="/import" className="text-sm text-primary hover:underline mt-2 inline-block">
                  Import your first statement
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {recentTransactions.slice(0, 8).map((txn) => (
                  <div key={txn.id} className="flex items-center justify-between p-3 rounded-lg hover:bg-secondary transition-colors" data-testid={`transaction-${txn.id}`}>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{txn.description}</p>
                      <p className="text-sm text-muted-foreground">{format(new Date(txn.date), 'MMM dd, yyyy')}</p>
                    </div>
                    <div className={`text-lg font-semibold ${txn.direction === 'CREDIT' ? 'text-green-600' : 'text-red-600'}`}>
                      {txn.direction === 'CREDIT' ? '+' : '-'}₹{txn.amount.toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card data-testid="accounts-card">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Accounts</CardTitle>
              <Link to="/accounts" className="text-sm text-primary hover:underline" data-testid="manage-accounts-link">
                Manage
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {accounts.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Wallet className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="mb-2">No accounts added</p>
                <Link to="/accounts" className="text-sm text-primary hover:underline">
                  Add your first account
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {accounts.map((account) => (
                  <div key={account.id} className="p-4 rounded-lg border bg-card" data-testid={`account-${account.id}`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-semibold">{account.name}</p>
                        <p className="text-sm text-muted-foreground">{account.institution}</p>
                        {account.last_four && (
                          <p className="text-xs text-muted-foreground mt-1">****{account.last_four}</p>
                        )}
                      </div>
                      <div className={`px-2 py-1 rounded text-xs font-medium ${
                        account.account_type === 'BANK' 
                          ? 'bg-blue-500/10 text-blue-700' 
                          : 'bg-purple-500/10 text-purple-700'
                      }`}>
                        {account.account_type === 'BANK' ? 'Bank' : 'Credit Card'}
                      </div>
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

export default DashboardPage;
