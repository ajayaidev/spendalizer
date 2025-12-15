import React, { useContext } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { AuthContext } from '../../App';
import { 
  LayoutDashboard, 
  Wallet, 
  Upload, 
  Receipt, 
  Tag,
  Sparkles, 
  BarChart3,
  TrendingUp,
  Settings,
  LogOut 
} from 'lucide-react';
import { Button } from '../ui/button';

const DashboardLayout = () => {
  const { user, logout } = useContext(AuthContext);

  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/accounts', label: 'Accounts', icon: Wallet },
    { to: '/import', label: 'Import', icon: Upload },
    { to: '/transactions', label: 'Transactions', icon: Receipt },
    { to: '/categories', label: 'Categories', icon: Tag },
    { to: '/rules', label: 'Rules', icon: Sparkles },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-background" data-testid="dashboard-layout">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-card hidden md:block" data-testid="sidebar">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b">
            <h1 className="text-2xl font-bold tracking-tight" data-testid="app-logo">SpendAlizer</h1>
            <p className="text-sm text-muted-foreground mt-1">Financial Insights</p>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2" data-testid="sidebar-nav">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                data-testid={`nav-link-${item.label.toLowerCase()}`}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-md transition-all duration-200 ${isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-secondary text-foreground'
                  }`
                }
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </NavLink>
            ))}
          </nav>

          {/* User Info */}
          <div className="p-4 border-t">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <span className="text-sm font-semibold text-primary">
                  {user?.name?.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate" data-testid="user-name">{user?.name}</p>
                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={logout}
              data-testid="logout-button"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto relative" data-testid="main-content">
        <Outlet />
      </main>
    </div>
  );
};

export default DashboardLayout;
