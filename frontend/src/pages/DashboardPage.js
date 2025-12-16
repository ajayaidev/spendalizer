import React, { useState, useEffect } from 'react';
import { getAnalyticsSummary } from '../lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Calendar } from '../components/ui/calendar';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';
import { TrendingUp, TrendingDown, PieChart as PieChartIcon, Calendar as CalendarIcon } from 'lucide-react';
import { format, subMonths, startOfMonth, endOfMonth, startOfYear, endOfYear } from 'date-fns';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

const COLORS = ['hsl(221, 83%, 53%)', 'hsl(142, 76%, 36%)', 'hsl(35, 92%, 55%)', 'hsl(262, 83%, 58%)', 'hsl(346, 87%, 43%)'];
const UNCATEGORIZED_COLOR = 'hsl(0, 0%, 60%)'; // Gray for uncategorized

const DashboardPage = () => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({ from: null, to: null });

  useEffect(() => {
    loadData();
  }, [dateRange]);

  const loadData = async () => {
    try {
      const params = {};
      if (dateRange.from) params.start_date = format(dateRange.from, 'yyyy-MM-dd');
      if (dateRange.to) params.end_date = format(dateRange.to, 'yyyy-MM-dd');
      
      const response = await getAnalyticsSummary(params);
      setSummary(response.data);
    } catch (error) {
      toast.error('Failed to load analytics');
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
    return <div className="flex items-center justify-center min-h-screen">Loading dashboard...</div>;
  }

  const expenseCategories = summary?.category_breakdown
    ?.filter((cat) => cat.category_type === 'EXPENSE')
    .sort((a, b) => b.total - a.total) || [];

  const incomeCategories = summary?.category_breakdown
    ?.filter((cat) => cat.category_type === 'INCOME')
    .sort((a, b) => b.total - a.total) || [];

  // Internal Transfers (bank-to-bank, doesn't affect net worth)
  const internalTransferInCategories = summary?.category_breakdown?.filter(
    (cat) => cat.category_type === 'TRANSFER_INTERNAL_IN' || cat.category_type === 'TRANSFER_IN'
  ) || [];

  const internalTransferOutCategories = summary?.category_breakdown?.filter(
    (cat) => cat.category_type === 'TRANSFER_INTERNAL_OUT' || cat.category_type === 'TRANSFER_OUT'
  ) || [];

  // External Transfers (investments, loans, affects net worth)
  const externalTransferInCategories = summary?.category_breakdown?.filter(
    (cat) => cat.category_type === 'TRANSFER_EXTERNAL_IN'
  ) || [];

  const externalTransferOutCategories = summary?.category_breakdown?.filter(
    (cat) => cat.category_type === 'TRANSFER_EXTERNAL_OUT'
  ) || [];

  const uncategorizedData = summary?.category_breakdown?.find(
    (cat) => cat.category_type === 'UNCATEGORIZED'
  );

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

      {/* Uncategorized Alert */}
      {uncategorizedData && uncategorizedData.count > 0 && (
        <Card className="mb-6 border-yellow-200 bg-yellow-50" data-testid="uncategorized-alert">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-full bg-yellow-500/20 flex items-center justify-center flex-shrink-0">
                <PieChartIcon className="w-6 h-6 text-yellow-700" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-yellow-900 mb-1">
                  {uncategorizedData.count} Uncategorized Transaction{uncategorizedData.count !== 1 ? 's' : ''}
                </h3>
                <p className="text-sm text-yellow-800 mb-3">
                  You have ₹{uncategorizedData.total.toLocaleString()} in uncategorized transactions. 
                  Categorizing them will improve your spending insights and analytics.
                </p>
                <a 
                  href="/transactions" 
                  className="text-sm font-medium text-yellow-900 hover:text-yellow-700 underline"
                >
                  Review and categorize →
                </a>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Financial Flow Overview - Three Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* INFLOW Column */}
        <Card>
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-2xl text-green-600 dark:text-green-400">Total Inflow</CardTitle>
              <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/50">
                <TrendingUp className="w-6 h-6 text-green-600 dark:text-green-400" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Main Total */}
            <div className="pb-4 border-b">
              <div className="text-4xl font-bold text-green-600">
                ₹{summary?.total_income?.toLocaleString() || '0'}
              </div>
            </div>

            {/* Breakdown */}
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-12 rounded-full bg-green-600"></div>
                  <div>
                    <p className="font-medium text-sm">Income</p>
                    <p className="text-xs text-muted-foreground">Salary, business, etc.</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-green-700 dark:text-green-400">
                    ₹{incomeCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {((incomeCategories.reduce((sum, cat) => sum + cat.total, 0) / (summary?.total_income || 1)) * 100).toFixed(0)}%
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between p-3">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-12 rounded-full bg-cyan-600"></div>
                  <div>
                    <p className="font-medium text-sm">External IN</p>
                    <p className="text-xs text-muted-foreground">Refunds, returns</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-cyan-700 dark:text-cyan-400">
                    ₹{externalTransferInCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {((externalTransferInCategories.reduce((sum, cat) => sum + cat.total, 0) / (summary?.total_income || 1)) * 100).toFixed(0)}%
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between p-3">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-12 rounded-full bg-teal-600"></div>
                  <div>
                    <p className="font-medium text-sm">Internal IN</p>
                    <p className="text-xs text-muted-foreground">Transfers between accounts</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-teal-700 dark:text-teal-400">
                    ₹{internalTransferInCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {((internalTransferInCategories.reduce((sum, cat) => sum + cat.total, 0) / (summary?.total_income || 1)) * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* OUTFLOW Column */}
        <Card>
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-2xl text-red-600 dark:text-red-400">Total Outflow</CardTitle>
              <div className="p-2 rounded-lg bg-red-100 dark:bg-red-900/50">
                <TrendingDown className="w-6 h-6 text-red-600 dark:text-red-400" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Main Total */}
            <div className="pb-4 border-b">
              <div className="text-4xl font-bold text-red-600">
                ₹{summary?.total_expense?.toLocaleString() || '0'}
              </div>
            </div>

            {/* Breakdown */}
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-12 rounded-full bg-red-600"></div>
                  <div>
                    <p className="font-medium text-sm">Expenses</p>
                    <p className="text-xs text-muted-foreground">Food, bills, shopping</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-red-700 dark:text-red-400">
                    ₹{expenseCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {((expenseCategories.reduce((sum, cat) => sum + cat.total, 0) / (summary?.total_expense || 1)) * 100).toFixed(0)}%
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between p-3">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-12 rounded-full bg-orange-600"></div>
                  <div>
                    <p className="font-medium text-sm">External OUT</p>
                    <p className="text-xs text-muted-foreground">Investments, loans</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-orange-700 dark:text-orange-400">
                    ₹{externalTransferOutCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {((externalTransferOutCategories.reduce((sum, cat) => sum + cat.total, 0) / (summary?.total_expense || 1)) * 100).toFixed(0)}%
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between p-3">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-12 rounded-full bg-purple-600"></div>
                  <div>
                    <p className="font-medium text-sm">Internal OUT</p>
                    <p className="text-xs text-muted-foreground">Transfers between accounts</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-purple-700 dark:text-purple-400">
                    ₹{internalTransferOutCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {((internalTransferOutCategories.reduce((sum, cat) => sum + cat.total, 0) / (summary?.total_expense || 1)) * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* NET SAVINGS Column */}
        <Card className="overflow-hidden">
          <CardHeader className={`pb-4 bg-gradient-to-br ${
            (summary?.net_savings || 0) >= 0 
              ? 'from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30'
              : 'from-orange-50 to-red-50 dark:from-orange-950/30 dark:to-red-950/30'
          }`}>
            <div className="flex items-center justify-between">
              <CardTitle className="text-2xl">Net Savings</CardTitle>
              <div className={`p-2 rounded-lg ${
                (summary?.net_savings || 0) >= 0 
                  ? 'bg-blue-100 dark:bg-blue-900/50' 
                  : 'bg-orange-100 dark:bg-orange-900/50'
              }`}>
                <PieChartIcon className={`w-6 h-6 ${
                  (summary?.net_savings || 0) >= 0 
                    ? 'text-blue-600 dark:text-blue-400' 
                    : 'text-orange-600 dark:text-orange-400'
                }`} />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Main Total */}
            <div className="pb-4 border-b">
              <div className={`text-4xl font-bold ${
                (summary?.net_savings || 0) >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                ₹{summary?.net_savings?.toLocaleString() || '0'}
              </div>
            </div>

            {/* Insights */}
            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-muted">
                <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Status</p>
                <p className="font-bold text-lg">
                  {(summary?.net_savings || 0) >= 0 ? '✓ Surplus' : '⚠ Deficit'}
                </p>
              </div>

              <div className="p-3 rounded-lg bg-muted">
                <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Savings Rate</p>
                <p className="font-bold text-lg">
                  {summary?.total_income && summary?.net_savings 
                    ? `${((summary.net_savings / summary.total_income) * 100).toFixed(1)}%`
                    : '0%'}
                </p>
              </div>

              <div className="p-3 rounded-lg bg-muted">
                <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Efficiency</p>
                <p className="font-bold text-lg">
                  {summary?.total_income && summary?.total_expense
                    ? `${((summary.total_expense / summary.total_income) * 100).toFixed(0)}% spent`
                    : '0% spent'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Income and Expense Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Income Categories */}
        <Card data-testid="top-income-card">
          <CardHeader>
            <CardTitle>Top Income Sources</CardTitle>
            <CardDescription>Your main income categories</CardDescription>
          </CardHeader>
          <CardContent>
            {incomeCategories.length > 0 ? (
              <div className="space-y-4">
                {incomeCategories.slice(0, 5).map((cat, index) => (
                  <div key={cat.category_name || 'uncategorized'} className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1">
                      <div 
                        className="w-2 h-12 rounded-full" 
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{cat.category_name || 'Uncategorized'}</p>
                        <p className="text-sm text-muted-foreground">
                          {((cat.total / (summary.total_income || 1)) * 100).toFixed(1)}% of income
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-green-600">₹{cat.total.toLocaleString()}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-[240px] text-muted-foreground">
                <p>No income data available</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top Expense Categories */}
        <Card data-testid="top-expense-card">
          <CardHeader>
            <CardTitle>Top Expense Categories</CardTitle>
            <CardDescription>Where your money goes</CardDescription>
          </CardHeader>
          <CardContent>
            {expenseCategories.length > 0 ? (
              <div className="space-y-4">
                {expenseCategories.slice(0, 5).map((cat, index) => (
                  <div key={cat.category_name || 'uncategorized'} className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1">
                      <div 
                        className="w-2 h-12 rounded-full" 
                        style={{ backgroundColor: cat.category_name === 'Uncategorized' ? UNCATEGORIZED_COLOR : COLORS[index % COLORS.length] }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{cat.category_name || 'Uncategorized'}</p>
                        <p className="text-sm text-muted-foreground">
                          {((cat.total / (summary.total_expense || 1)) * 100).toFixed(1)}% of expenses
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-red-600">₹{cat.total.toLocaleString()}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-[240px] text-muted-foreground">
                <p>No expense data available</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Uncategorized Alert */}
      {uncategorizedData && uncategorizedData.count > 0 && (
        <Card className="mt-6 border-yellow-200 bg-yellow-50" data-testid="category-uncategorized">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-semibold text-yellow-900">Uncategorized</p>
                  <span className="px-2 py-0.5 rounded-full bg-yellow-200 text-yellow-800 text-xs font-medium">
                    Needs Review
                  </span>
                </div>
                <p className="text-sm text-yellow-700 mt-1">{uncategorizedData.count} transactions</p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-yellow-900">₹{uncategorizedData.total.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Analytics Cards Layout - 2 columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                {/* Income Card */}
                <Card className="border-green-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-green-700 text-lg">Income</CardTitle>
                    {incomeCategories.length > 0 && (
                      <CardDescription className="text-2xl font-bold text-green-900 mt-2">
                        ₹{incomeCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                  {incomeCategories.length > 0 ? (
                    <div className="space-y-4">
                      {/* Income Pie Chart */}
                      <div className="flex justify-center">
                        <ResponsiveContainer width="100%" height={200}>
                          <PieChart>
                            <Pie
                              data={(() => {
                                const topIncome = incomeCategories.slice(0, 5);
                                const othersIncome = incomeCategories.slice(5);
                                const pieData = topIncome.map(cat => ({
                                  name: cat.category_name,
                                  value: cat.total
                                }));
                                if (othersIncome.length > 0) {
                                  pieData.push({
                                    name: 'All Others',
                                    value: othersIncome.reduce((sum, cat) => sum + cat.total, 0)
                                  });
                                }
                                return pieData;
                              })()}
                              cx="50%"
                              cy="50%"
                              innerRadius={50}
                              outerRadius={80}
                              paddingAngle={2}
                              dataKey="value"
                            >
                              {incomeCategories.slice(0, 5).map((_, index) => (
                                <Cell key={`cell-${index}`} fill={`hsl(${142 + index * 20}, 70%, ${40 + index * 10}%)`} />
                              ))}
                              {incomeCategories.length > 5 && (
                                <Cell fill="hsl(142, 30%, 70%)" />
                              )}
                            </Pie>
                            <Tooltip formatter={(value) => `₹${value.toLocaleString()}`} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      
                      {/* Top 5 Income Categories */}
                      <div className="space-y-2">
                        {incomeCategories.slice(0, 5).map((cat, index) => (
                          <div key={index} className="flex items-center gap-3">
                            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: `hsl(${142 + index * 20}, 70%, ${40 + index * 10}%)` }}></div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-green-900 text-sm truncate">{cat.category_name}</p>
                            </div>
                            <div className="text-right">
                              <p className="font-semibold text-green-900 text-sm">₹{cat.total.toLocaleString()}</p>
                            </div>
                          </div>
                        ))}
                        {incomeCategories.length > 5 && (
                          <div className="flex items-center gap-3">
                            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: 'hsl(142, 30%, 70%)' }}></div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-green-700 text-sm">All Others</p>
                            </div>
                            <div className="text-right">
                              <p className="font-semibold text-green-900 text-sm">
                                ₹{incomeCategories.slice(5).reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg">
                      <p className="text-sm">No income categories</p>
                    </div>
                  )}
                  </CardContent>
                </Card>

                {/* Expense Card */}
                <Card className="border-red-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-red-700 text-lg">Expenses</CardTitle>
                    {expenseCategories.length > 0 && (
                      <CardDescription className="text-2xl font-bold text-red-900 mt-2">
                        ₹{expenseCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                  {expenseCategories.length > 0 ? (
                    <div className="space-y-4">
                      {/* Expense Pie Chart */}
                      <div className="flex justify-center">
                        <ResponsiveContainer width="100%" height={200}>
                          <PieChart>
                            <Pie
                              data={(() => {
                                const topExpense = expenseCategories.slice(0, 5);
                                const othersExpense = expenseCategories.slice(5);
                                const pieData = topExpense.map(cat => ({
                                  name: cat.category_name,
                                  value: cat.total
                                }));
                                if (othersExpense.length > 0) {
                                  pieData.push({
                                    name: 'All Others',
                                    value: othersExpense.reduce((sum, cat) => sum + cat.total, 0)
                                  });
                                }
                                return pieData;
                              })()}
                              cx="50%"
                              cy="50%"
                              innerRadius={50}
                              outerRadius={80}
                              paddingAngle={2}
                              dataKey="value"
                            >
                              {expenseCategories.slice(0, 5).map((_, index) => (
                                <Cell key={`cell-${index}`} fill={`hsl(${0 + index * 20}, 70%, ${50 + index * 8}%)`} />
                              ))}
                              {expenseCategories.length > 5 && (
                                <Cell fill="hsl(0, 30%, 70%)" />
                              )}
                            </Pie>
                            <Tooltip formatter={(value) => `₹${value.toLocaleString()}`} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      
                      {/* Top 5 Expense Categories */}
                      <div className="space-y-2">
                        {expenseCategories.slice(0, 5).map((cat, index) => (
                          <div key={index} className="flex items-center gap-3">
                            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: `hsl(${0 + index * 20}, 70%, ${50 + index * 8}%)` }}></div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-red-900 text-sm truncate">{cat.category_name}</p>
                            </div>
                            <div className="text-right">
                              <p className="font-semibold text-red-900 text-sm">₹{cat.total.toLocaleString()}</p>
                            </div>
                          </div>
                        ))}
                        {expenseCategories.length > 5 && (
                          <div className="flex items-center gap-3">
                            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: 'hsl(0, 30%, 70%)' }}></div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-red-700 text-sm">All Others</p>
                            </div>
                            <div className="text-right">
                              <p className="font-semibold text-red-900 text-sm">
                                ₹{expenseCategories.slice(5).reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg">
                      <p className="text-sm">No expense categories</p>
                    </div>
                  )}
                  </CardContent>
                </Card>

                {/* External Transfers IN Card */}
                <Card className="border-teal-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-teal-700 text-lg">External Transfers IN</CardTitle>
                    <CardDescription className="text-xs text-teal-600">Incoming investments, returns - affects net worth</CardDescription>
                    {externalTransferInCategories.length > 0 && (
                      <CardDescription className="text-2xl font-bold text-teal-900 mt-2">
                        ₹{externalTransferInCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                  {externalTransferInCategories.length > 0 ? (
                    <div className="space-y-2">
                      {externalTransferInCategories.map((cat, index) => (
                        <div key={index} className="flex items-center gap-3">
                          <div className="w-3 h-3 rounded-full flex-shrink-0 bg-teal-500"></div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-teal-900 text-sm truncate">{cat.category_name}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-semibold text-teal-900 text-sm">₹{cat.total.toLocaleString()}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg">
                      <p className="text-sm">No external incoming transfers</p>
                    </div>
                  )}
                  </CardContent>
                </Card>

                {/* External Transfers OUT Card */}
                <Card className="border-orange-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-orange-700 text-lg">External Transfers OUT</CardTitle>
                    <CardDescription className="text-xs text-orange-600">Investments, loans - affects net worth</CardDescription>
                    {externalTransferOutCategories.length > 0 && (
                      <CardDescription className="text-2xl font-bold text-orange-900 mt-2">
                        ₹{externalTransferOutCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                  {externalTransferOutCategories.length > 0 ? (
                    <div className="space-y-2">
                      {externalTransferOutCategories.map((cat, index) => (
                        <div key={index} className="flex items-center gap-3">
                          <div className="w-3 h-3 rounded-full flex-shrink-0 bg-orange-500"></div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-orange-900 text-sm truncate">{cat.category_name}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-semibold text-orange-900 text-sm">₹{cat.total.toLocaleString()}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg">
                      <p className="text-sm">No external transfers out</p>
                    </div>
                  )}
                  </CardContent>
                </Card>

                {/* Internal Transfers IN (Bank Transfers) Card */}
                <Card className="border-blue-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-blue-700 text-lg">Internal Transfers IN</CardTitle>
                    <CardDescription className="text-xs text-blue-600">Bank-to-bank, doesn't affect net worth</CardDescription>
                    {internalTransferInCategories.length > 0 && (
                      <CardDescription className="text-2xl font-bold text-blue-900 mt-2">
                        ₹{internalTransferInCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                  {internalTransferInCategories.length > 0 ? (
                    <div className="space-y-4">
                      {/* Incoming Transfer Pie Chart */}
                      <div className="flex justify-center">
                        <ResponsiveContainer width="100%" height={200}>
                          <PieChart>
                            <Pie
                              data={(() => {
                                const topTransfer = internalTransferInCategories.slice(0, 5);
                                const othersTransfer = internalTransferInCategories.slice(5);
                                const pieData = topTransfer.map(cat => ({
                                  name: cat.category_name,
                                  value: cat.total
                                }));
                                if (othersTransfer.length > 0) {
                                  pieData.push({
                                    name: 'All Others',
                                    value: othersTransfer.reduce((sum, cat) => sum + cat.total, 0)
                                  });
                                }
                                return pieData;
                              })()}
                              cx="50%"
                              cy="50%"
                              innerRadius={50}
                              outerRadius={80}
                              paddingAngle={2}
                              dataKey="value"
                            >
                              {internalTransferInCategories.slice(0, 5).map((_, index) => (
                                <Cell key={`cell-${index}`} fill={`hsl(${200 + index * 20}, 70%, ${50 + index * 8}%)`} />
                              ))}
                              {internalTransferInCategories.length > 5 && (
                                <Cell fill="hsl(200, 30%, 70%)" />
                              )}
                            </Pie>
                            <Tooltip formatter={(value) => `₹${value.toLocaleString()}`} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      
                      {/* Top 5 Internal Transfer IN Categories */}
                      <div className="space-y-2">
                        {internalTransferInCategories.slice(0, 5).map((cat, index) => (
                          <div key={index} className="flex items-center gap-3">
                            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: `hsl(${200 + index * 20}, 70%, ${50 + index * 8}%)` }}></div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-blue-900 text-sm truncate">{cat.category_name}</p>
                            </div>
                            <div className="text-right">
                              <p className="font-semibold text-blue-900 text-sm">₹{cat.total.toLocaleString()}</p>
                            </div>
                          </div>
                        ))}
                        {internalTransferInCategories.length > 5 && (
                          <div className="flex items-center gap-3">
                            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: 'hsl(200, 30%, 70%)' }}></div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-blue-700 text-sm">All Others</p>
                            </div>
                            <div className="text-right">
                              <p className="font-semibold text-blue-900 text-sm">
                                ₹{internalTransferInCategories.slice(5).reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg">
                      <p className="text-sm">No internal incoming transfers</p>
                    </div>
                  )}
                  </CardContent>
                </Card>

                {/* Internal Transfers OUT Card */}
                <Card className="border-purple-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-purple-700 text-lg">Internal Transfers OUT</CardTitle>
                    <CardDescription className="text-xs text-purple-600">Bank-to-bank, doesn't affect net worth</CardDescription>
                    {internalTransferOutCategories.length > 0 && (
                      <CardDescription className="text-2xl font-bold text-purple-900 mt-2">
                        ₹{internalTransferOutCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                  {internalTransferOutCategories.length > 0 ? (
                    <div className="space-y-4">
                      {/* Internal Outgoing Transfer Pie Chart */}
                      <div className="flex justify-center">
                        <ResponsiveContainer width="100%" height={200}>
                          <PieChart>
                            <Pie
                              data={(() => {
                                const topTransfer = internalTransferOutCategories.slice(0, 5);
                                const othersTransfer = internalTransferOutCategories.slice(5);
                                const pieData = topTransfer.map(cat => ({
                                  name: cat.category_name,
                                  value: cat.total
                                }));
                                if (othersTransfer.length > 0) {
                                  pieData.push({
                                    name: 'All Others',
                                    value: othersTransfer.reduce((sum, cat) => sum + cat.total, 0)
                                  });
                                }
                                return pieData;
                              })()}
                              cx="50%"
                              cy="50%"
                              innerRadius={50}
                              outerRadius={80}
                              paddingAngle={2}
                              dataKey="value"
                            >
                              {internalTransferOutCategories.slice(0, 5).map((_, index) => (
                                <Cell key={`cell-${index}`} fill={`hsl(${270 + index * 20}, 70%, ${50 + index * 8}%)`} />
                              ))}
                              {internalTransferOutCategories.length > 5 && (
                                <Cell fill="hsl(270, 30%, 70%)" />
                              )}
                            </Pie>
                            <Tooltip formatter={(value) => `₹${value.toLocaleString()}`} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      
                      {/* Top 5 Internal Outgoing Transfer Categories */}
                      <div className="space-y-2">
                        {internalTransferOutCategories.slice(0, 5).map((cat, index) => (
                          <div key={index} className="flex items-center gap-3">
                            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: `hsl(${270 + index * 20}, 70%, ${50 + index * 8}%)` }}></div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-purple-900 text-sm truncate">{cat.category_name}</p>
                            </div>
                            <div className="text-right">
                              <p className="font-semibold text-purple-900 text-sm">₹{cat.total.toLocaleString()}</p>
                            </div>
                          </div>
                        ))}
                        {internalTransferOutCategories.length > 5 && (
                          <div className="flex items-center gap-3">
                            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: 'hsl(270, 30%, 70%)' }}></div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-purple-700 text-sm">All Others</p>
                            </div>
                            <div className="text-right">
                              <p className="font-semibold text-purple-900 text-sm">
                                ₹{internalTransferOutCategories.slice(5).reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg">
                      <p className="text-sm">No internal outgoing transfers</p>
                    </div>
                  )}
                  </CardContent>
                </Card>
              </div>
    </div>
  );
};

export default DashboardPage;
