import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Calendar } from '../components/ui/calendar';
import { Checkbox } from '../components/ui/checkbox';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Calendar as CalendarIcon, ChevronDown, ChevronRight, TrendingUp } from 'lucide-react';
import { format, subMonths, startOfMonth, endOfMonth } from 'date-fns';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Color palette for different categories
const COLORS = [
  'hsl(142, 76%, 36%)', // Green
  'hsl(0, 84%, 60%)',   // Red
  'hsl(221, 83%, 53%)', // Blue
  'hsl(189, 85%, 44%)', // Cyan
  'hsl(271, 76%, 53%)', // Purple
  'hsl(25, 95%, 53%)',  // Orange
  'hsl(180, 62%, 45%)', // Teal
  'hsl(35, 92%, 55%)',  // Yellow
  'hsl(346, 87%, 43%)', // Pink
  'hsl(262, 83%, 58%)', // Violet
];

const TrendReportPage = () => {
  // Default to "Last Month" date range
  const [dateRange, setDateRange] = useState({
    from: startOfMonth(subMonths(new Date(), 1)),
    to: endOfMonth(subMonths(new Date(), 1))
  });
  const [trendData, setTrendData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategories, setSelectedCategories] = useState(new Set());
  // Default to Income and Expenses groups selected
  const [selectedGroups, setSelectedGroups] = useState(new Set(['INCOME', 'EXPENSE']));
  const [expandedGroups, setExpandedGroups] = useState(new Set());

  useEffect(() => {
    loadTrendData();
  }, [dateRange]);

  const loadTrendData = async () => {
    try {
      const token = localStorage.getItem('token');
      const params = {
        group_by: 'month'
      };
      if (dateRange.from) params.start_date = format(dateRange.from, 'yyyy-MM-dd');
      if (dateRange.to) params.end_date = format(dateRange.to, 'yyyy-MM-dd');

      const response = await axios.get(`${BACKEND_URL}/api/analytics/category-trends`, {
        params,
        headers: { Authorization: `Bearer ${token}` }
      });

      setTrendData(response.data);
    } catch (error) {
      toast.error('Failed to load trend data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDateFilter = (option) => {
    const today = new Date();
    switch (option) {
      case 'last_month':
        setDateRange({ 
          from: startOfMonth(subMonths(today, 1)), 
          to: endOfMonth(subMonths(today, 1)) 
        });
        break;
      case 'last_3_months':
        setDateRange({ from: subMonths(today, 3), to: today });
        break;
      case 'last_6_months':
        setDateRange({ from: subMonths(today, 6), to: today });
        break;
      case 'last_12_months':
        setDateRange({ from: subMonths(today, 12), to: today });
        break;
      default:
        break;
    }
  };

  const toggleCategory = (categoryId) => {
    const newSelected = new Set(selectedCategories);
    if (newSelected.has(categoryId)) {
      newSelected.delete(categoryId);
    } else {
      newSelected.add(categoryId);
    }
    setSelectedCategories(newSelected);
  };

  const toggleGroup = (groupType) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupType)) {
      newExpanded.delete(groupType);
    } else {
      newExpanded.add(groupType);
    }
    setExpandedGroups(newExpanded);
  };

  const toggleGroupSelection = (groupType) => {
    const newSelectedGroups = new Set(selectedGroups);
    if (newSelectedGroups.has(groupType)) {
      newSelectedGroups.delete(groupType);
    } else {
      newSelectedGroups.add(groupType);
    }
    setSelectedGroups(newSelectedGroups);
  };

  // Group categories by type
  const groupCategories = () => {
    if (!trendData) return [];

    const groups = [
      { key: 'INCOME', title: 'Income', categories: [] },
      { key: 'EXPENSE', title: 'Expense', categories: [] },
      { key: 'TRANSFER_INTERNAL_IN', title: 'Internal Transfer IN', categories: [] },
      { key: 'TRANSFER_INTERNAL_OUT', title: 'Internal Transfer OUT', categories: [] },
      { key: 'TRANSFER_EXTERNAL_IN', title: 'External Transfer IN', categories: [] },
      { key: 'TRANSFER_EXTERNAL_OUT', title: 'External Transfer OUT', categories: [] },
    ];

    trendData.categories.forEach(cat => {
      const group = groups.find(g => g.key === cat.type);
      if (group) {
        group.categories.push(cat);
      }
    });

    return groups.filter(g => g.categories.length > 0);
  };

  // Prepare chart data
  const getChartData = () => {
    if (!trendData || (selectedCategories.size === 0 && selectedGroups.size === 0)) return [];

    const groups = groupCategories();
    
    return trendData.periods.map(period => {
      const dataPoint = { period };
      
      // Add selected group totals
      selectedGroups.forEach(groupKey => {
        const group = groups.find(g => g.key === groupKey);
        if (group) {
          const groupTotal = group.categories.reduce((sum, cat) => {
            return sum + (trendData.data[period]?.[cat.id] || 0);
          }, 0);
          dataPoint[`group_${groupKey}`] = groupTotal;
        }
      });
      
      // Add selected individual categories
      selectedCategories.forEach(catId => {
        const category = trendData.categories.find(c => c.id === catId);
        if (category) {
          dataPoint[catId] = trendData.data[period]?.[catId] || 0;
        }
      });
      
      return dataPoint;
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading trend report...</div>
      </div>
    );
  }

  const categoryGroups = groupCategories();
  const chartData = getChartData();

  return (
    <div className="container mx-auto px-4 py-8 md:px-8 md:py-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-2">Trend Report</h1>
          <p className="text-muted-foreground">Category-wise spending trends over time</p>
        </div>

        {/* Date Range Filter */}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickDateFilter('last_month')}
          >
            Last Month
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickDateFilter('last_3_months')}
          >
            Last 3 Months
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickDateFilter('last_6_months')}
          >
            Last 6 Months
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickDateFilter('last_12_months')}
          >
            Last 12 Months
          </Button>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm">
                <CalendarIcon className="mr-2 h-4 w-4" />
                {dateRange.from && dateRange.to
                  ? `${format(dateRange.from, 'MMM dd')} - ${format(dateRange.to, 'MMM dd, yyyy')}`
                  : 'Custom Range'}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="end">
              <Calendar
                mode="range"
                selected={{ from: dateRange.from, to: dateRange.to }}
                onSelect={(range) => {
                  if (range?.from && range?.to) {
                    setDateRange({ from: range.from, to: range.to });
                  }
                }}
                numberOfMonths={2}
              />
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {/* Trend Graph */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Category Trends</CardTitle>
          <CardDescription>
            {selectedCategories.size === 0 && selectedGroups.size === 0
              ? 'Select category groups or individual categories from the table below to view trends'
              : `Showing ${selectedGroups.size} group${selectedGroups.size === 1 ? '' : 's'} and ${selectedCategories.size} categor${selectedCategories.size === 1 ? 'y' : 'ies'}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {chartData.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <TrendingUp className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p>Select category groups or individual categories from the table below to view trends</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" />
                <YAxis tickFormatter={(value) => `₹${value.toLocaleString()}`} />
                <Tooltip formatter={(value) => `₹${value.toLocaleString()}`} />
                <Legend />
                {/* Render selected group trends */}
                {Array.from(selectedGroups).map((groupKey, index) => {
                  const groups = groupCategories();
                  const group = groups.find(g => g.key === groupKey);
                  return (
                    <Line
                      key={`group_${groupKey}`}
                      type="monotone"
                      dataKey={`group_${groupKey}`}
                      stroke={COLORS[index % COLORS.length]}
                      strokeWidth={3}
                      name={group?.title || groupKey}
                      strokeDasharray="5 5"
                    />
                  );
                })}
                {/* Render selected individual category trends */}
                {Array.from(selectedCategories).map((catId, index) => {
                  const category = trendData.categories.find(c => c.id === catId);
                  const colorIndex = (index + selectedGroups.size) % COLORS.length;
                  return (
                    <Line
                      key={catId}
                      type="monotone"
                      dataKey={catId}
                      stroke={COLORS[colorIndex]}
                      strokeWidth={2}
                      name={category?.name || 'Unknown'}
                    />
                  );
                })}
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Category Table */}
      <Card>
        <CardHeader>
          <CardTitle>Category Breakdown</CardTitle>
          <CardDescription>Monthly spending by category</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-3 font-semibold sticky left-0 bg-background">Category</th>
                  {trendData?.periods.map(period => (
                    <th key={period} className="text-right p-3 font-semibold min-w-[100px]">
                      {period}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {categoryGroups.map(group => (
                  <React.Fragment key={group.key}>
                    {/* Group Header */}
                    <tr className="bg-muted/50 hover:bg-muted border-b">
                      <td className="p-3 font-semibold sticky left-0 bg-muted/50">
                        <div className="flex items-center gap-2">
                          <Checkbox
                            checked={selectedGroups.has(group.key)}
                            onCheckedChange={() => toggleGroupSelection(group.key)}
                          />
                          <button
                            onClick={() => toggleGroup(group.key)}
                            className="flex items-center gap-2 hover:text-primary"
                          >
                            {expandedGroups.has(group.key) ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : (
                              <ChevronRight className="w-4 h-4" />
                            )}
                            <span>{group.title}</span>
                          </button>
                        </div>
                      </td>
                      {trendData?.periods.map(period => {
                        const groupTotal = group.categories.reduce((sum, cat) => {
                          return sum + (trendData.data[period]?.[cat.id] || 0);
                        }, 0);
                        return (
                          <td key={period} className="text-right p-3 font-semibold">
                            ₹{groupTotal.toLocaleString()}
                          </td>
                        );
                      })}
                    </tr>

                    {/* Category Rows */}
                    {expandedGroups.has(group.key) &&
                      group.categories.map(category => (
                        <tr key={category.id} className="border-b hover:bg-muted/30">
                          <td className="p-3 pl-8 sticky left-0 bg-background">
                            <div className="flex items-center gap-2">
                              <Checkbox
                                checked={selectedCategories.has(category.id)}
                                onCheckedChange={() => toggleCategory(category.id)}
                              />
                              <span>{category.name}</span>
                            </div>
                          </td>
                          {trendData?.periods.map(period => (
                            <td key={period} className="text-right p-3">
                              {trendData.data[period]?.[category.id]
                                ? `₹${trendData.data[period][category.id].toLocaleString()}`
                                : '-'}
                            </td>
                          ))}
                        </tr>
                      ))}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default TrendReportPage;
