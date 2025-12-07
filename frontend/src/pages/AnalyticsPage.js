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

      {/* Three Cards Layout for Desktop */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
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

                {/* Transfer Card */}
                <Card className="border-blue-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-blue-700 text-lg">Transfers</CardTitle>
                    {transferCategories.length > 0 && (
                      <CardDescription className="text-2xl font-bold text-blue-900 mt-2">
                        ₹{transferCategories.reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                  {transferCategories.length > 0 ? (
                    <div className="space-y-4">
                      {/* Transfer Pie Chart */}
                      <div className="flex justify-center">
                        <ResponsiveContainer width="100%" height={200}>
                          <PieChart>
                            <Pie
                              data={(() => {
                                const topTransfer = transferCategories.slice(0, 5);
                                const othersTransfer = transferCategories.slice(5);
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
                              {transferCategories.slice(0, 5).map((_, index) => (
                                <Cell key={`cell-${index}`} fill={`hsl(${221 + index * 20}, 70%, ${50 + index * 8}%)`} />
                              ))}
                              {transferCategories.length > 5 && (
                                <Cell fill="hsl(221, 30%, 70%)" />
                              )}
                            </Pie>
                            <Tooltip formatter={(value) => `₹${value.toLocaleString()}`} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      
                      {/* Top 5 Transfer Categories */}
                      <div className="space-y-2">
                        {transferCategories.slice(0, 5).map((cat, index) => (
                          <div key={index} className="flex items-center gap-3">
                            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: `hsl(${221 + index * 20}, 70%, ${50 + index * 8}%)` }}></div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-blue-900 text-sm truncate">{cat.category_name}</p>
                            </div>
                            <div className="text-right">
                              <p className="font-semibold text-blue-900 text-sm">₹{cat.total.toLocaleString()}</p>
                            </div>
                          </div>
                        ))}
                        {transferCategories.length > 5 && (
                          <div className="flex items-center gap-3">
                            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: 'hsl(221, 30%, 70%)' }}></div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-blue-700 text-sm">All Others</p>
                            </div>
                            <div className="text-right">
                              <p className="font-semibold text-blue-900 text-sm">
                                ₹{transferCategories.slice(5).reduce((sum, cat) => sum + cat.total, 0).toLocaleString()}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground border border-dashed rounded-lg">
                      <p className="text-sm">No transfer categories</p>
                    </div>
                  )}
                  </CardContent>
                </Card>
              </div>
    </div>
  );
};

export default AnalyticsPage;
