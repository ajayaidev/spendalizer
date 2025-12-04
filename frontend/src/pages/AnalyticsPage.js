import React, { useState, useEffect } from 'react';
import { getAnalyticsSummary } from '../lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { TrendingUp, TrendingDown, PieChart as PieChartIcon } from 'lucide-react';
import { toast } from 'sonner';

const COLORS = ['hsl(221, 83%, 53%)', 'hsl(142, 76%, 36%)', 'hsl(35, 92%, 55%)', 'hsl(262, 83%, 58%)', 'hsl(346, 87%, 43%)'];

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
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
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
          <CardDescription>Detailed spending by category</CardDescription>
        </CardHeader>
        <CardContent>
          {expenseCategories.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>No expense data available</p>
            </div>
          ) : (
            <div className="space-y-4">
              {expenseCategories.map((cat, index) => (
                <div key={index} className="flex items-center justify-between" data-testid={`category-${cat.category_id}`}>
                  <div className="flex-1">
                    <p className="font-medium">{cat.category_name}</p>
                    <p className="text-sm text-muted-foreground">{cat.count} transactions</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold">₹{cat.total.toLocaleString()}</p>
                    <p className="text-xs text-muted-foreground">
                      {((cat.total / summary.total_expense) * 100).toFixed(1)}% of total
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AnalyticsPage;
