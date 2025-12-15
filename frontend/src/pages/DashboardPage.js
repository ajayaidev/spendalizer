import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getAnalyticsSummary, getTransactions, getAccounts, getSpendingOverTime } from '../lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Calendar } from '../components/ui/calendar';
import { Checkbox } from '../components/ui/checkbox';
import { Label } from '../components/ui/label';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, Wallet, Receipt, Calendar as CalendarIcon } from 'lucide-react';
import { format, subMonths, startOfMonth, endOfMonth, startOfYear, endOfYear } from 'date-fns';
import { cn } from '../lib/utils';

const DashboardPage = () => {
  const [summary, setSummary] = useState(null);
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({ from: null, to: null });
  const [trendData, setTrendData] = useState([]);
  const [visibleLines, setVisibleLines] = useState({
    income: true,
    expense: true,
    net: true,
    transfer_internal_in: false,
    transfer_internal_out: false,
    transfer_external_in: false,
    transfer_external_out: false
  });

  useEffect(() => {
    loadData();
  }, [dateRange]);

  const loadData = async () => {
    try {
      const params = { limit: 10 };
      const trendParams = { group_by: 'month' };
      if (dateRange.from) {
        params.start_date = format(dateRange.from, 'yyyy-MM-dd');
        trendParams.start_date = format(dateRange.from, 'yyyy-MM-dd');
      }
      if (dateRange.to) {
        params.end_date = format(dateRange.to, 'yyyy-MM-dd');
        trendParams.end_date = format(dateRange.to, 'yyyy-MM-dd');
      }

      const [summaryRes, txnRes, accountsRes, trendRes] = await Promise.all([
        getAnalyticsSummary(dateRange.from ? params : {}),
        getTransactions(params),
        getAccounts(),
        getSpendingOverTime(trendParams)
      ]);
      setSummary(summaryRes.data);
      setRecentTransactions(txnRes.data.transactions);
      setAccounts(accountsRes.data);
      setTrendData(trendRes.data);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDateFilter = (option) => {
    const today = new Date();
    switch (option) {
      case 'this_month':
        setDateRange({ from: startOfMonth(today), to: endOfMonth(today) });
        break;
      case 'last_month':
        const lastMonth = subMonths(today, 1);
        setDateRange({ from: startOfMonth(lastMonth), to: endOfMonth(lastMonth) });
        break;
      case 'last_3_months':
        setDateRange({ from: subMonths(today, 3), to: today });
        break;
      case 'last_6_months':
        setDateRange({ from: subMonths(today, 6), to: today });
        break;
      case 'this_year':
        setDateRange({ from: startOfYear(today), to: endOfYear(today) });
        break;
      case 'clear':
        setDateRange({ from: null, to: null });
        break;
      default:
        break;
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
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
          <div>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-2">Dashboard</h1>
            <p className="text-muted-foreground">Your financial overview at a glance</p>
          </div>
          
          {/* Date Filter */}
          <div className="flex flex-wrap gap-2">
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
                    <span>All Time</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="end">
                <div className="p-3 border-b space-y-1">
                  <Button variant="ghost" className="w-full justify-start" onClick={() => handleQuickDateFilter('this_month')}>
                    This Month
                  </Button>
                  <Button variant="ghost" className="w-full justify-start" onClick={() => handleQuickDateFilter('last_month')}>
                    Last Month
                  </Button>
                  <Button variant="ghost" className="w-full justify-start" onClick={() => handleQuickDateFilter('last_3_months')}>
                    Last 3 Months
                  </Button>
                  <Button variant="ghost" className="w-full justify-start" onClick={() => handleQuickDateFilter('last_6_months')}>
                    Last 6 Months
                  </Button>
                  <Button variant="ghost" className="w-full justify-start" onClick={() => handleQuickDateFilter('this_year')}>
                    This Year
                  </Button>
                  <Button variant="ghost" className="w-full justify-start" onClick={() => handleQuickDateFilter('clear')}>
                    Clear Filter
                  </Button>
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
        </div>
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

      {/* Trend Graph */}
      <Card className="mt-6">
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <CardTitle>Financial Trends</CardTitle>
              <CardDescription>Track your income and expenses over time</CardDescription>
            </div>
            <div className="flex flex-wrap gap-4">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="income-toggle"
                  checked={visibleLines.income}
                  onCheckedChange={(checked) => setVisibleLines({ ...visibleLines, income: checked })}
                />
                <Label htmlFor="income-toggle" className="text-sm font-medium cursor-pointer">
                  <span className="inline-block w-3 h-3 rounded-full bg-green-500 mr-1"></span>
                  Income
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="expense-toggle"
                  checked={visibleLines.expense}
                  onCheckedChange={(checked) => setVisibleLines({ ...visibleLines, expense: checked })}
                />
                <Label htmlFor="expense-toggle" className="text-sm font-medium cursor-pointer">
                  <span className="inline-block w-3 h-3 rounded-full bg-red-500 mr-1"></span>
                  Expense
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="net-toggle"
                  checked={visibleLines.net}
                  onCheckedChange={(checked) => setVisibleLines({ ...visibleLines, net: checked })}
                />
                <Label htmlFor="net-toggle" className="text-sm font-medium cursor-pointer">
                  <span className="inline-block w-3 h-3 rounded-full bg-blue-500 mr-1"></span>
                  Net
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="transfer-internal-in-toggle"
                  checked={visibleLines.transfer_internal_in}
                  onCheckedChange={(checked) => setVisibleLines({ ...visibleLines, transfer_internal_in: checked })}
                />
                <Label htmlFor="transfer-internal-in-toggle" className="text-sm font-medium cursor-pointer">
                  <span className="inline-block w-3 h-3 rounded-full bg-cyan-500 mr-1"></span>
                  Internal IN
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="transfer-internal-out-toggle"
                  checked={visibleLines.transfer_internal_out}
                  onCheckedChange={(checked) => setVisibleLines({ ...visibleLines, transfer_internal_out: checked })}
                />
                <Label htmlFor="transfer-internal-out-toggle" className="text-sm font-medium cursor-pointer">
                  <span className="inline-block w-3 h-3 rounded-full bg-purple-500 mr-1"></span>
                  Internal OUT
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="transfer-external-in-toggle"
                  checked={visibleLines.transfer_external_in}
                  onCheckedChange={(checked) => setVisibleLines({ ...visibleLines, transfer_external_in: checked })}
                />
                <Label htmlFor="transfer-external-in-toggle" className="text-sm font-medium cursor-pointer">
                  <span className="inline-block w-3 h-3 rounded-full bg-teal-500 mr-1"></span>
                  External IN
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="transfer-external-out-toggle"
                  checked={visibleLines.transfer_external_out}
                  onCheckedChange={(checked) => setVisibleLines({ ...visibleLines, transfer_external_out: checked })}
                />
                <Label htmlFor="transfer-external-out-toggle" className="text-sm font-medium cursor-pointer">
                  <span className="inline-block w-3 h-3 rounded-full bg-orange-500 mr-1"></span>
                  External OUT
                </Label>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {trendData.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <p>No trend data available for the selected period</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" />
                <YAxis tickFormatter={(value) => `₹${value.toLocaleString()}`} />
                <Tooltip formatter={(value) => `₹${value.toLocaleString()}`} />
                <Legend />
                {visibleLines.income && (
                  <Line type="monotone" dataKey="income" stroke="hsl(142, 76%, 36%)" strokeWidth={2} name="Income" />
                )}
                {visibleLines.expense && (
                  <Line type="monotone" dataKey="expense" stroke="hsl(0, 84%, 60%)" strokeWidth={2} name="Expense" />
                )}
                {visibleLines.net && (
                  <Line type="monotone" dataKey="net" stroke="hsl(221, 83%, 53%)" strokeWidth={2} name="Net" />
                )}
                {visibleLines.transfer_internal_in && (
                  <Line type="monotone" dataKey="transfer_internal_in" stroke="hsl(189, 85%, 44%)" strokeWidth={2} name="Internal IN" />
                )}
                {visibleLines.transfer_internal_out && (
                  <Line type="monotone" dataKey="transfer_internal_out" stroke="hsl(271, 76%, 53%)" strokeWidth={2} name="Internal OUT" />
                )}
                {visibleLines.transfer_external_in && (
                  <Line type="monotone" dataKey="transfer_external_in" stroke="hsl(180, 62%, 45%)" strokeWidth={2} name="External IN" />
                )}
                {visibleLines.transfer_external_out && (
                  <Line type="monotone" dataKey="transfer_external_out" stroke="hsl(25, 95%, 53%)" strokeWidth={2} name="External OUT" />
                )}
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

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
