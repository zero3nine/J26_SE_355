import React, { useState } from 'react';
import {
  Briefcase,
  ShieldCheck,
  UserCheck,
  Eye,
  EyeOff,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Sparkles,
  Layers,
  Globe,
  Database,
  BarChart3,
  Lock,
  Mail,
  Info,
  Compass,
} from 'lucide-react';

interface LoginPageProps {
  onNavigateToHome: () => void;
  onNavigateToApp: (targetPath?: string) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({
  onNavigateToHome,
  onNavigateToApp,
}) => {
  const [accountType, setAccountType] = useState<'user' | 'admin'>('user');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  const handleRoleSelect = (role: 'user' | 'admin') => {
    setAccountType(role);
    if (!email || email === 'analyst@research.sliit.lk' || email === 'admin.collector@research.sliit.lk') {
      setEmail(role === 'admin' ? 'admin.collector@research.sliit.lk' : 'analyst@research.sliit.lk');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setNotification(
      `Authenticated successfully as ${
        accountType === 'admin' ? 'Platform Administrator' : 'Research Analyst'
      } (Demo Session). Redirecting to console...`
    );

    setTimeout(() => {
      setIsLoading(false);
      onNavigateToApp(accountType === 'admin' ? '/pages/1_Collect_Data' : '/dashboard');
    }, 600);
  };

  const handleDirectDemoAccess = (target: string = '/dashboard') => {
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      onNavigateToApp(target);
    }, 300);
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#172033] flex flex-col justify-between selection:bg-blue-100 selection:text-blue-900">
      {/* Top Bar with Return Navigation */}
      <header className="border-b border-[#E2E8F0] bg-white/90 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <button
            onClick={onNavigateToHome}
            className="inline-flex items-center gap-2 text-xs font-semibold text-[#64748B] hover:text-[#2563EB] transition-colors group"
          >
            <ArrowLeft className="w-4 h-4 text-[#64748B] group-hover:-translate-x-0.5 transition-transform" />
            <span>Return to Public Portal Overview</span>
          </button>

          <div className="flex items-center gap-2 text-xs text-[#64748B]">
            <span className="hidden sm:inline">Research Evaluation Environment</span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-medium border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Live Sandbox
            </span>
          </div>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10 md:py-16 flex items-center justify-center">
        <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-stretch">
          
          {/* Left Column: Research Platform Branding & Highlights */}
          <div className="lg:col-span-6 flex flex-col justify-between space-y-8 bg-gradient-to-br from-slate-900 via-[#14213d] to-slate-900 rounded-3xl p-8 sm:p-10 text-white shadow-xl relative overflow-hidden">
            {/* Background decorative glows */}
            <div className="absolute top-0 right-0 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>
            <div className="absolute bottom-0 left-0 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none -ml-20 -mb-20"></div>

            <div className="relative z-10 space-y-6">
              {/* Institution badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-xs font-medium text-blue-200">
                <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                <span>SLIIT Undergraduate Research • Faculty of Computing</span>
              </div>

              {/* Title & Scope */}
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-xl bg-blue-600/30 border border-blue-400/30 flex items-center justify-center text-blue-300">
                    <Briefcase className="w-6 h-6" />
                  </div>
                  <div>
                    <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                      IT Job Advertisement Data Collector & Analytics Platform
                    </h1>
                    <p className="text-xs text-blue-200 font-mono">
                      Project Reference: J26-SE-355
                    </p>
                  </div>
                </div>

                <p className="text-sm text-slate-300 leading-relaxed pt-2">
                  Quantitative Analysis Framework for Technical Skill Identification in IT Sector Jobs.
                  An empirical academic workbench providing multi-country labour market telemetry, automated ETL pipelines, and normalized skill intelligence.
                </p>
              </div>

              {/* Research pillars summary */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-4 border-t border-white/10">
                <div className="flex items-start gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
                  <Globe className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs font-semibold text-white">4 National Markets</div>
                    <div className="text-[11px] text-slate-400">Sri Lanka (Focal), IN, SG, MY</div>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
                  <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs font-semibold text-white">SSRF Security Active</div>
                    <div className="text-[11px] text-slate-400">Strict domain whitelisting</div>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
                  <BarChart3 className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs font-semibold text-white">Statistical Similarity</div>
                    <div className="text-[11px] text-slate-400">Cosine, Jaccard & Spearman</div>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
                  <Database className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs font-semibold text-white">14 Analysis Modules</div>
                    <div className="text-[11px] text-slate-400">From scraping to ML clustering</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Card in Left Column */}
            <div className="relative z-10 pt-6 border-t border-white/10">
              <div className="p-4 rounded-2xl bg-blue-900/40 border border-blue-400/20 backdrop-blur-sm flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-blue-300" />
                    Peer Evaluation Mode Enabled
                  </div>
                  <div className="text-[11px] text-blue-200 mt-0.5">
                    No credentials required for project assessment.
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleDirectDemoAccess('/dashboard')}
                  className="px-3 py-1.5 rounded-lg bg-white text-slate-900 text-xs font-bold hover:bg-blue-50 transition-colors shrink-0 shadow-sm"
                >
                  Skip Login →
                </button>
              </div>
            </div>
          </div>

          {/* Right Column: Interactive Login UI Form */}
          <div className="lg:col-span-6 flex flex-col justify-center">
            <div className="bg-white rounded-3xl border border-[#E2E8F0] shadow-sm p-6 sm:p-10 space-y-6">
              {/* Form Title */}
              <div className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#2563EB]">
                  Console Access
                </span>
                <h2 className="text-2xl font-bold tracking-tight text-[#172033]">
                  Sign in to Research Platform
                </h2>
                <p className="text-xs text-[#64748B]">
                  Choose your role below to simulate appropriate permission sets and access privileges.
                </p>
              </div>

              {/* Account Type Selector (User vs Administrator) */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-[#172033] block">
                  Select Account Type
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {/* Option 1: User */}
                  <button
                    type="button"
                    onClick={() => handleRoleSelect('user')}
                    className={`relative p-3.5 rounded-2xl border text-left transition-all ${
                      accountType === 'user'
                        ? 'border-[#2563EB] bg-blue-50/70 text-[#172033] ring-2 ring-blue-500/20 shadow-xs'
                        : 'border-[#E2E8F0] bg-white text-[#64748B] hover:border-slate-300 hover:bg-slate-50/60'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          accountType === 'user'
                            ? 'bg-[#2563EB] text-white shadow-xs'
                            : 'bg-slate-100 text-[#64748B]'
                        }`}
                      >
                        <UserCheck className="w-4 h-4" />
                      </div>
                      {accountType === 'user' && (
                        <span className="w-2 h-2 rounded-full bg-[#2563EB]"></span>
                      )}
                    </div>
                    <div className="text-xs font-bold text-[#172033]">Research User</div>
                    <div className="text-[11px] text-[#64748B] mt-0.5 leading-snug">
                      Analytics exploration, dashboards & reports
                    </div>
                  </button>

                  {/* Option 2: Administrator */}
                  <button
                    type="button"
                    onClick={() => handleRoleSelect('admin')}
                    className={`relative p-3.5 rounded-2xl border text-left transition-all ${
                      accountType === 'admin'
                        ? 'border-[#2563EB] bg-blue-50/70 text-[#172033] ring-2 ring-blue-500/20 shadow-xs'
                        : 'border-[#E2E8F0] bg-white text-[#64748B] hover:border-slate-300 hover:bg-slate-50/60'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          accountType === 'admin'
                            ? 'bg-[#2563EB] text-white shadow-xs'
                            : 'bg-slate-100 text-[#64748B]'
                        }`}
                      >
                        <ShieldCheck className="w-4 h-4" />
                      </div>
                      {accountType === 'admin' && (
                        <span className="w-2 h-2 rounded-full bg-[#2563EB]"></span>
                      )}
                    </div>
                    <div className="text-xs font-bold text-[#172033]">Administrator</div>
                    <div className="text-[11px] text-[#64748B] mt-0.5 leading-snug">
                      Scraper control, domain validation & ETL
                    </div>
                  </button>
                </div>

                {/* Account role guidance pill */}
                <div className="rounded-xl bg-slate-50 border border-[#E2E8F0] p-3 text-[11px] text-[#64748B] flex items-start gap-2">
                  <Info className="w-4 h-4 text-[#2563EB] shrink-0 mt-0.5" />
                  <div>
                    {accountType === 'admin' ? (
                      <span>
                        <strong className="text-[#172033]">Administrator Mode:</strong> Grants access to live web scraper controls, SSRF security domain approval, failure log audits, and benchmark snapshot generation.
                      </span>
                    ) : (
                      <span>
                        <strong className="text-[#172033]">User Mode:</strong> Grants read-only exploration of regional benchmarks, skill relationship graphs, temporal distributions, and curriculum gap analyses.
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Login Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Email / Username */}
                <div className="space-y-1.5">
                  <label
                    htmlFor="email-input"
                    className="text-xs font-semibold text-[#172033] flex items-center justify-between"
                  >
                    <span>Academic Email or Research ID</span>
                    <span className="text-[10px] text-[#64748B] font-normal">Pre-filled for Demo</span>
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#64748B]">
                      <Mail className="h-4 w-4" />
                    </div>
                    <input
                      id="email-input"
                      type="text"
                      value={email || (accountType === 'admin' ? 'admin.collector@research.sliit.lk' : 'analyst@research.sliit.lk')}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder={accountType === 'admin' ? 'admin.collector@research.sliit.lk' : 'analyst@research.sliit.lk'}
                      required
                      className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-[#E2E8F0] bg-white text-xs text-[#172033] placeholder:text-slate-400 focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-500/20 shadow-2xs transition-all"
                    />
                  </div>
                </div>

                {/* Password Input */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label
                      htmlFor="password-input"
                      className="text-xs font-semibold text-[#172033]"
                    >
                      Password
                    </label>
                    <button
                      type="button"
                      onClick={() =>
                        alert(
                          'Evaluation Environment Note: For academic demonstration, any password string will successfully authenticate.'
                        )
                      }
                      className="text-[11px] font-medium text-[#2563EB] hover:underline"
                    >
                      Forgot Password?
                    </button>
                  </div>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#64748B]">
                      <Lock className="h-4 w-4" />
                    </div>
                    <input
                      id="password-input"
                      type={showPassword ? 'text' : 'password'}
                      value={password || 'academic-eval-2026'}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="w-full pl-9 pr-10 py-2.5 rounded-xl border border-[#E2E8F0] bg-white text-xs text-[#172033] placeholder:text-slate-400 focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-500/20 shadow-2xs transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#64748B] hover:text-[#172033]"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Remember Me Checkbox */}
                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="rounded border-[#E2E8F0] text-[#2563EB] focus:ring-blue-500/20 h-4 w-4"
                    />
                    <span className="text-xs text-[#64748B]">Keep session active on this workstation</span>
                  </label>
                </div>

                {/* Notification Banner */}
                {notification && (
                  <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2 animate-fade-in">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span>{notification}</span>
                  </div>
                )}

                {/* Primary Submit Button */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#2563EB] px-5 py-3 text-xs sm:text-sm font-semibold text-white shadow-sm hover:bg-[#1D4ED8] active:scale-[0.99] transition-all disabled:opacity-75 cursor-pointer"
                >
                  {isLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      <span>Initializing Session...</span>
                    </>
                  ) : (
                    <>
                      <span>
                        Enter Console as {accountType === 'admin' ? 'Administrator' : 'Research User'}
                      </span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>

              {/* Divider */}
              <div className="relative flex items-center justify-center">
                <div className="border-t border-[#E2E8F0] w-full"></div>
                <span className="bg-white px-3 text-[11px] uppercase tracking-wider text-[#64748B] font-semibold absolute">
                  Or instant access
                </span>
              </div>

              {/* Direct Evaluator Access Options */}
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => handleDirectDemoAccess('/dashboard')}
                  className="w-full inline-flex items-center justify-between rounded-xl border border-[#E2E8F0] bg-slate-50/70 hover:bg-slate-100/80 px-4 py-2.5 text-xs font-semibold text-[#172033] shadow-2xs transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-[#2563EB]" />
                    <span>Launch Research Dashboard Directly</span>
                  </div>
                  <span className="text-[11px] text-[#64748B]">No Sign-in →</span>
                </button>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => handleDirectDemoAccess('/pages/1_Collect_Data')}
                    className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-[#E2E8F0] bg-white hover:bg-slate-50 px-3 py-2 text-[11px] font-medium text-[#172033] shadow-2xs transition-colors"
                  >
                    <Layers className="w-3.5 h-3.5 text-[#64748B]" />
                    <span>Collect Data</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleDirectDemoAccess('/pages/12_Regional_Analysis')}
                    className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-[#E2E8F0] bg-white hover:bg-slate-50 px-3 py-2 text-[11px] font-medium text-[#172033] shadow-2xs transition-colors"
                  >
                    <Compass className="w-3.5 h-3.5 text-[#64748B]" />
                    <span>Regional Analysis</span>
                  </button>
                </div>
              </div>

              {/* Security & Academic Note */}
              <div className="pt-2 border-t border-[#E2E8F0] text-[11px] text-center text-[#64748B] space-y-1">
                <div>
                  Academic Frontend Demonstration • Client-Side Role Switching
                </div>
                <div className="text-[10px] text-slate-400">
                  Protected under SLIIT Computing Faculty Ethical Research Guidelines
                </div>
              </div>
            </div>
          </div>

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#E2E8F0] bg-white py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#64748B]">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-[#172033]">J26-SE-355</span>
            <span>•</span>
            <span>Quantitative Analysis Framework for Technical Skill Identification in IT Sector Jobs</span>
          </div>
          <div>
            SLIIT Undergraduate Research © 2026. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
};
