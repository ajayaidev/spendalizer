import React, { useContext, useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
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
  LogOut,
  ChevronDown,
  ChevronRight,
  Menu,
  X
} from 'lucide-react';
import { Button } from '../ui/button';

const DashboardLayout = () => {
  const { user, logout } = useContext(AuthContext);
  const location = useLocation();
  const [expandedMenus, setExpandedMenus] = useState(new Set(['analytics']));
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleMenu = (key) => {
    const newExpanded = new Set(expandedMenus);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedMenus(newExpanded);
  };

  // Close mobile menu when route changes
  const handleNavClick = () => {
    setMobileMenuOpen(false);
  };

  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/accounts', label: 'Accounts', icon: Wallet },
    { to: '/import', label: 'Import', icon: Upload },
    { to: '/transactions', label: 'Transactions', icon: Receipt },
    { to: '/categories', label: 'Categories', icon: Tag },
    { to: '/rules', label: 'Rules', icon: Sparkles },
    { 
      key: 'analytics',
      label: 'Analytics', 
      icon: BarChart3,
      submenu: [
        { to: '/analytics', label: 'Overview', icon: BarChart3 },
        { to: '/trend-report', label: 'Trend Report', icon: TrendingUp },
      ]
    },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  const renderNavItems = (isMobile = false) => (
    <>
      {navItems.map((item) => {
        if (item.submenu) {
          const isExpanded = expandedMenus.has(item.key);
          const isAnySubmenuActive = item.submenu.some(sub => location.pathname === sub.to);
          
          return (
            <div key={item.key}>
              <button
                onClick={() => toggleMenu(item.key)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-all duration-200 ${
                  isAnySubmenuActive
                    ? 'bg-primary/10 text-primary'
                    : 'hover:bg-secondary text-foreground'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium flex-1 text-left">{item.label}</span>
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </button>
              {isExpanded && (
                <div className="ml-4 mt-1 space-y-1">
                  {item.submenu.map((subItem) => (
                    <NavLink
                      key={subItem.to}
                      to={subItem.to}
                      onClick={isMobile ? handleNavClick : undefined}
                      data-testid={`nav-link-${subItem.label.toLowerCase().replace(' ', '-')}`}
                      className={({ isActive }) =>
                        `flex items-center gap-3 px-4 py-2 rounded-md transition-all duration-200 text-sm ${
                          isActive
                            ? 'bg-gradient-to-r from-fuchsia-600 to-violet-800 text-white shadow-md'
                            : 'hover:bg-gradient-to-r hover:from-fuchsia-50 hover:to-violet-100 text-foreground'
                        }`
                      }
                    >
                      <subItem.icon className="w-4 h-4" />
                      <span className="font-medium">{subItem.label}</span>
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          );
        }
        
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            onClick={isMobile ? handleNavClick : undefined}
            data-testid={`nav-link-${item.label.toLowerCase()}`}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-md transition-all duration-200 ${
                isActive
                  ? 'bg-gradient-to-r from-fuchsia-600 to-violet-800 text-white shadow-md'
                  : 'hover:bg-gradient-to-r hover:from-fuchsia-50 hover:to-violet-100 text-foreground'
              }`
            }
          >
            <item.icon className="w-5 h-5" />
            <span className="font-medium">{item.label}</span>
          </NavLink>
        );
      })}
    </>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background" data-testid="dashboard-layout">
      {/* Mobile Header */}
      <div className="fixed top-0 left-0 right-0 z-50 md:hidden bg-card border-b">
        <div className="flex items-center justify-between p-4">
          <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-fuchsia-600 to-violet-800 bg-clip-text text-transparent">
            SpendAlizer
          </h1>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            data-testid="mobile-menu-button"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </Button>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Mobile Sidebar */}
      <aside 
        className={`fixed top-0 left-0 z-50 h-full w-72 bg-card border-r transform transition-transform duration-300 ease-in-out md:hidden ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        data-testid="mobile-sidebar"
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-fuchsia-600 to-violet-800 bg-clip-text text-transparent">
                SpendAlizer
              </h1>
              <p className="text-sm text-muted-foreground mt-1">Financial Insights</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setMobileMenuOpen(false)}
            >
              <X className="w-5 h-5" />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {renderNavItems(true)}
          </nav>

          {/* User Info */}
          <div className="p-4 border-t">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-r from-fuchsia-600 to-violet-800 flex items-center justify-center shadow-md">
                <span className="text-sm font-semibold text-white">
                  {user?.name?.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user?.name}</p>
                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => { logout(); setMobileMenuOpen(false); }}
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </aside>

      {/* Desktop Sidebar */}
      <aside className="w-64 border-r bg-card hidden md:block" data-testid="sidebar">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b">
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-fuchsia-600 to-violet-800 bg-clip-text text-transparent" data-testid="app-logo">SpendAlizer</h1>
            <p className="text-sm text-muted-foreground mt-1">Financial Insights</p>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1" data-testid="sidebar-nav">
            {renderNavItems(false)}
          </nav>

          {/* User Info */}
          <div className="p-4 border-t">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-r from-fuchsia-600 to-violet-800 flex items-center justify-center shadow-md">
                <span className="text-sm font-semibold text-white">
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
      <main className="flex-1 overflow-y-auto relative pt-16 md:pt-0" data-testid="main-content">
        <Outlet />
      </main>
    </div>
  );
};

export default DashboardLayout;
