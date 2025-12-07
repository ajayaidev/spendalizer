import React, { useState, useEffect } from 'react';
import { getAnalyticsSummary } from '../lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { TrendingUp, TrendingDown, PieChart as PieChartIcon } from 'lucide-react';
import { toast } from 'sonner';

const COLORS = ['hsl(221, 83%, 53%)', 'hsl(142, 76%, 36%)', 'hsl(35, 92%, 55%)', 'hsl(262, 83%, 58%)', 'hsl(346, 87%, 43%)'];
const UNCATEGORIZED_COLOR = 'hsl(0, 0%, 60%)'; // Gray for uncategorized

const AnalyticsPage = () => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const response = await getAnalyticsSummary();
      setSummary(response.data);
    } catch (error) {
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading analytics...</div>;
  }

  const expenseCategories = summary?.category_breakdown?.filter(
    (cat) => cat.category_type === 'EXPENSE'
  ) || [];

  const incomeCategories = summary?.category_breakdown?.filter(
    (cat) => cat.category_type === 'INCOME'
  ) || [];

  const transferCategories = summary?.category_breakdown?.filter(
    (cat) => cat.category_type === 'TRANSFER'
  ) || [];

  const uncategorizedData = summary?.category_breakdown?.find(
    (cat) => cat.category_type === 'UNCATEGORIZED'
  );

  // Include uncategorized in top expenses if it exists
  const topExpenses = expenseCategories.slice(0, uncategorizedData ? 4 : 5);
  const pieData = [
    ...topExpenses.map((cat) => ({
      name: cat.category_name,
      value: cat.total
    })),
    ...(uncategorizedData ? [{
      name: 'Uncategorized',
      value: uncategorizedData.total
    }] : [])
  ];

  const overviewData = [
    { name: 'Income', value: summary?.total_income || 0, color: 'hsl(142, 76%, 36%)' },
    { name: 'Expense', value: summary?.total_expense || 0, color: 'hsl(0, 84.2%, 60.2%)' },
  ];

  return (
    <div className="container mx-auto px-4 py-8 md:px-8 md:py-12" data-testid="analytics-page">
      <div className="mb-8">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-2">Analytics</h1>
        <p className="text-muted-foreground">Insights into your spending and saving patterns</p>
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

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card data-testid="total-income-card">
          <CardHeader className="pb-3">
            <CardDescription className="text-xs uppercase tracking-wide">Total Income</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="text-3xl font-bold text-green-600">
                ₹{summary?.total_income?.toLocaleString() || '0'}
              </div>
              <TrendingUp className="w-8 h-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card data-testid="total-expense-card">
          <CardHeader className="pb-3">
            <CardDescription className="text-xs uppercase tracking-wide">Total Expense</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="text-3xl font-bold text-red-600">
                ₹{summary?.total_expense?.toLocaleString() || '0'}
              </div>
              <TrendingDown className="w-8 h-8 text-red-600" />
            </div>
          </CardContent>
        </Card>

        <Card data-testid="net-savings-card">
          <CardHeader className="pb-3">
            <CardDescription className="text-xs uppercase tracking-wide">Net Savings</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className={`text-3xl font-bold ${
                (summary?.net_savings || 0) >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                ₹{summary?.net_savings?.toLocaleString() || '0'}
              </div>
              <PieChartIcon className="w-8 h-8 text-primary" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Income vs Expense Bar Chart */}
        <Card data-testid="income-expense-chart">
          <CardHeader>
            <CardTitle>Income vs Expense</CardTitle>
            <CardDescription>Overall comparison</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={overviewData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" />
                <YAxis stroke="hsl(var(--muted-foreground))" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.5rem'
                  }}
                />
                <Bar dataKey="value" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Expense Breakdown Pie Chart */}
        <Card data-testid="expense-breakdown-chart">
          <CardHeader>
            <CardTitle>Top Expense Categories</CardTitle>
            <CardDescription>Where your money goes</CardDescription>
          </CardHeader>
          <CardContent>
            {pieData.length === 0 ? (
              <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                <p>No expense data available</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={entry.name === 'Uncategorized' ? UNCATEGORIZED_COLOR : COLORS[index % COLORS.length]} 
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '0.5rem'
                    }}
                    formatter={(value) => `₹${value.toLocaleString()}`}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Category Breakdown Table */}
      <Card className="mt-6" data-testid="category-breakdown-table">
        <CardHeader>
          <CardTitle>Category Breakdown</CardTitle>
          <CardDescription>Detailed breakdown by Income, Expense, and Transfers</CardDescription>
        </CardHeader>
        <CardContent>
          {expenseCategories.length === 0 && incomeCategories.length === 0 && transferCategories.length === 0 && !uncategorizedData ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>No transaction data available</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Show uncategorized first if it exists */}
              {uncategorizedData && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wide">Uncategorized</h3>
                  <div 
                    className="flex items-center justify-between p-4 rounded-lg border-2 border-yellow-200 bg-yellow-50" 
                    data-testid="category-uncategorized"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-yellow-900">Uncategorized</p>
                        <span className="px-2 py-0.5 rounded-full bg-yellow-200 text-yellow-800 text-xs font-medium">
                          Needs Review
                        </span>
                      </div>
                      <p className="text-sm text-yellow-700">{uncategorizedData.count} transactions</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-semibold text-yellow-900">₹{uncategorizedData.total.toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Three Column Layout for Desktop */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Income Categories */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-green-700 uppercase tracking-wide">Income</h3>
                    <span className="text-sm text-muted-foreground">
                      ₹{incomeCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {incomeCategories.map((cat, index) => (
                      <div key={index} className="flex items-center justify-between p-3 rounded-lg border border-green-100 bg-green-50/50 hover:bg-green-50 transition-colors" data-testid={`category-income-${cat.category_id}`}>
                        <div className="flex-1">
                          <p className="font-medium text-green-900">{cat.category_name}</p>
                          <p className="text-sm text-green-700">{cat.count} transactions</p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-semibold text-green-900">₹{cat.total.toLocaleString()}</p>
                          <p className="text-xs text-green-700">
                            {((cat.total / summary.total_income) * 100).toFixed(1)}% of income
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Expense Categories */}
              {expenseCategories.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-red-700 uppercase tracking-wide">Expenses</h3>
                    <span className="text-sm text-muted-foreground">
                      ₹{expenseCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {expenseCategories.map((cat, index) => (
                      <div key={index} className="flex items-center justify-between p-3 rounded-lg border border-red-100 bg-red-50/50 hover:bg-red-50 transition-colors" data-testid={`category-expense-${cat.category_id}`}>
                        <div className="flex-1">
                          <p className="font-medium text-red-900">{cat.category_name}</p>
                          <p className="text-sm text-red-700">{cat.count} transactions</p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-semibold text-red-900">₹{cat.total.toLocaleString()}</p>
                          <p className="text-xs text-red-700">
                            {((cat.total / summary.total_expense) * 100).toFixed(1)}% of expenses
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Transfer Categories */}
              {transferCategories.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-blue-700 uppercase tracking-wide">Transfers</h3>
                    <span className="text-sm text-muted-foreground">
                      ₹{transferCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {transferCategories.map((cat, index) => (
                      <div key={index} className="flex items-center justify-between p-3 rounded-lg border border-blue-100 bg-blue-50/50 hover:bg-blue-50 transition-colors" data-testid={`category-transfer-${cat.category_id}`}>
                        <div className="flex-1">
                          <p className="font-medium text-blue-900">{cat.category_name}</p>
                          <p className="text-sm text-blue-700">{cat.count} transactions</p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-semibold text-blue-900">₹{cat.total.toLocaleString()}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AnalyticsPage;
