import React, { useState } from 'react';
import {
  Briefcase,
  Globe,
  ShieldCheck,
  Layers,
  Sparkles,
  Cpu,
  BarChart3,
  Database,
  TrendingUp,
  CheckCircle2,
  ArrowRight,
  Code2,
  Users,
  GraduationCap,
  Building2,
  FileText,
  Clock,
  ChevronRight,
  Menu,
  X,
  ExternalLink,
  DollarSign,
  AlertOctagon,
} from 'lucide-react';

interface LandingPageProps {
  onNavigateToLogin: () => void;
  onNavigateToApp: (targetPath?: string) => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onNavigateToLogin,
  onNavigateToApp,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeAudienceTab, setActiveAudienceTab] = useState<'students' | 'universities' | 'researchers' | 'industry'>('students');

  const scrollToSection = (id: string) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#172033] font-sans antialiased selection:bg-blue-100 selection:text-blue-900">
      {/* 1. Sticky Navigation Bar */}
      <header className="sticky top-0 z-50 w-full border-b border-[#E2E8F0] bg-white/90 backdrop-blur-md transition-all">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Logo & Platform Name */}
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-[#2563EB] border border-blue-100 shadow-2xs">
              <Briefcase className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold tracking-tight text-[#172033]">
                  IT Job Analytics
                </span>
                <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-[#2563EB] border border-blue-200">
                  SLIIT Research
                </span>
              </div>
              <p className="text-[11px] text-[#64748B] hidden sm:block">
                Technical Skill Identification & Labour-Market Intelligence
              </p>
            </div>
          </div>

          {/* Desktop Nav Links */}
          <nav className="hidden md:flex items-center gap-7 text-xs font-semibold text-[#64748B]">
            <button
              onClick={() => scrollToSection('home')}
              className="hover:text-[#2563EB] transition-colors"
            >
              Home
            </button>
            <button
              onClick={() => scrollToSection('about')}
              className="hover:text-[#2563EB] transition-colors"
            >
              About Research
            </button>
            <button
              onClick={() => scrollToSection('workflow')}
              className="hover:text-[#2563EB] transition-colors"
            >
              How It Works
            </button>
            <button
              onClick={() => scrollToSection('features')}
              className="hover:text-[#2563EB] transition-colors"
            >
              Features
            </button>
            <button
              onClick={() => scrollToSection('opportunities')}
              className="hover:text-[#2563EB] transition-colors"
            >
              Research Opportunities
            </button>
            <button
              onClick={() => scrollToSection('regional')}
              className="hover:text-[#2563EB] transition-colors"
            >
              Regional Focus
            </button>
          </nav>

          {/* Action CTAs */}
          <div className="hidden sm:flex items-center gap-3">
            <button
              onClick={onNavigateToLogin}
              className="rounded-xl border border-[#E2E8F0] bg-white px-4 py-2 text-xs font-semibold text-[#172033] shadow-2xs hover:border-[#2563EB] hover:text-[#2563EB] transition-all"
            >
              Sign In
            </button>
            <button
              onClick={() => onNavigateToApp('/dashboard')}
              className="inline-flex items-center gap-1.5 rounded-xl bg-[#2563EB] px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#1D4ED8] transition-all"
            >
              <span>Explore Platform</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-[#64748B] hover:text-[#172033]"
              aria-label="Toggle navigation"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-b border-[#E2E8F0] bg-white px-4 py-5 shadow-lg space-y-3 animate-in slide-in-from-top-2">
            <div className="flex flex-col space-y-2 text-sm font-medium text-[#172033]">
              <button
                onClick={() => scrollToSection('home')}
                className="text-left py-1.5 hover:text-[#2563EB]"
              >
                Home
              </button>
              <button
                onClick={() => scrollToSection('about')}
                className="text-left py-1.5 hover:text-[#2563EB]"
              >
                About Research
              </button>
              <button
                onClick={() => scrollToSection('workflow')}
                className="text-left py-1.5 hover:text-[#2563EB]"
              >
                How It Works
              </button>
              <button
                onClick={() => scrollToSection('features')}
                className="text-left py-1.5 hover:text-[#2563EB]"
              >
                Features
              </button>
              <button
                onClick={() => scrollToSection('opportunities')}
                className="text-left py-1.5 hover:text-[#2563EB]"
              >
                Research Opportunities
              </button>
              <button
                onClick={() => scrollToSection('regional')}
                className="text-left py-1.5 hover:text-[#2563EB]"
              >
                Regional Focus
              </button>
            </div>
            <div className="pt-3 border-t border-[#E2E8F0] flex flex-col gap-2">
              <button
                onClick={onNavigateToLogin}
                className="w-full rounded-xl border border-[#E2E8F0] py-2 text-center text-xs font-semibold text-[#172033]"
              >
                Sign In
              </button>
              <button
                onClick={() => onNavigateToApp('/dashboard')}
                className="w-full rounded-xl bg-[#2563EB] py-2 text-center text-xs font-semibold text-white"
              >
                Explore Platform
              </button>
            </div>
          </div>
        )}
      </header>

      {/* 2. Hero Section */}
      <section id="home" className="relative overflow-hidden pt-12 pb-20 lg:pt-20 lg:pb-32">
        {/* Subtle background decoration */}
        <div className="absolute top-1/4 left-1/2 -z-10 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-gradient-to-tr from-blue-100/40 via-sky-50/50 to-transparent blur-3xl opacity-70 pointer-events-none" />

        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-12 lg:grid-cols-12 lg:items-center">
            {/* Left Content Column */}
            <div className="lg:col-span-7 space-y-6">
              {/* Academic Project Badge */}
              <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50/80 px-3.5 py-1 text-xs font-semibold text-[#2563EB] shadow-2xs">
                <span className="flex h-2 w-2 rounded-full bg-[#2563EB] animate-pulse" />
                <span>SLIIT Undergraduate Research Project • Empirical Labour Market Intelligence</span>
              </div>

              {/* Main Heading */}
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-[#14213D] leading-[1.15]">
                Turning IT Job Market Data Into{' '}
                <span className="text-[#2563EB]">Meaningful Insights</span>
              </h1>

              {/* Supporting Description */}
              <p className="max-w-2xl text-base sm:text-lg text-[#64748B] leading-relaxed">
                A research-driven platform for collecting, validating, and analyzing IT job advertisements to uncover technical skill demand, understand labour-market trends, and explore opportunities across regional IT markets.
              </p>

              {/* CTAs */}
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button
                  onClick={() => scrollToSection('features')}
                  className="inline-flex items-center gap-2 rounded-xl bg-[#2563EB] px-6 py-3.5 text-xs sm:text-sm font-semibold text-white shadow-md hover:bg-[#1D4ED8] hover:shadow-lg transition-all"
                >
                  <span>Explore the Platform</span>
                  <ArrowRight className="h-4 w-4" />
                </button>

                <button
                  onClick={onNavigateToLogin}
                  className="inline-flex items-center gap-2 rounded-xl border border-[#E2E8F0] bg-white px-6 py-3.5 text-xs sm:text-sm font-semibold text-[#172033] shadow-xs hover:border-[#2563EB] hover:text-[#2563EB] hover:bg-slate-50 transition-all"
                >
                  Sign In
                </button>

                <button
                  onClick={() => onNavigateToApp('/dashboard')}
                  className="inline-flex items-center gap-1.5 px-4 py-3 text-xs font-semibold text-[#2563EB] hover:underline"
                >
                  <span>Launch Research Console</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </button>
              </div>

              {/* Highlights Micro-Strip */}
              <div className="grid grid-cols-3 gap-4 pt-6 border-t border-[#E2E8F0] text-left">
                <div>
                  <div className="text-xl sm:text-2xl font-extrabold text-[#14213D]">1,250+</div>
                  <div className="text-[11px] text-[#64748B] font-medium">Scraped IT Postings</div>
                </div>
                <div>
                  <div className="text-xl sm:text-2xl font-extrabold text-[#2563EB]">4 Markets</div>
                  <div className="text-[11px] text-[#64748B] font-medium">LK, IN, SG, MY</div>
                </div>
                <div>
                  <div className="text-xl sm:text-2xl font-extrabold text-[#16A34A]">80.7%</div>
                  <div className="text-[11px] text-[#64748B] font-medium">Macro Coverage Benchmark</div>
                </div>
              </div>
            </div>

            {/* Right Visual Column – Floating Analytics Dashboard Preview */}
            <div className="lg:col-span-5 relative">
              <div className="relative mx-auto w-full max-w-lg lg:max-w-none">
                {/* Main Card: Skill Demand Preview */}
                <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-xl space-y-4">
                  {/* Card Header */}
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <div className="flex items-center gap-2">
                      <div className="h-3 w-3 rounded-full bg-red-400" />
                      <div className="h-3 w-3 rounded-full bg-amber-400" />
                      <div className="h-3 w-3 rounded-full bg-emerald-400" />
                      <span className="ml-2 font-mono text-xs font-semibold text-[#172033]">
                        analytics_console.v2
                      </span>
                    </div>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-[#16A34A] border border-emerald-200">
                      <span className="h-1.5 w-1.5 rounded-full bg-[#16A34A] animate-ping" />
                      Live Feed
                    </span>
                  </div>

                  {/* Top Technical Skills Demand Bars */}
                  <div className="space-y-3">
                    <div className="flex justify-between text-xs font-semibold text-[#172033]">
                      <span>Technical Skill Demand (Focal Market)</span>
                      <span className="text-[#2563EB]">Relative Share</span>
                    </div>

                    {[
                      { skill: 'Python / Data Science', share: 64, color: 'bg-blue-600' },
                      { skill: 'React & TypeScript', share: 58, color: 'bg-sky-500' },
                      { skill: 'AWS / Cloud Infrastructure', share: 49, color: 'bg-indigo-600' },
                      { skill: 'Docker & Kubernetes', share: 42, color: 'bg-cyan-500' },
                      { skill: 'SQL & Database Architecture', share: 38, color: 'bg-emerald-600' },
                    ].map((item) => (
                      <div key={item.skill} className="space-y-1">
                        <div className="flex justify-between text-[11px]">
                          <span className="font-medium text-[#172033]">{item.skill}</span>
                          <span className="font-mono text-[#64748B]">{item.share}%</span>
                        </div>
                        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                          <div
                            className={`h-full ${item.color} rounded-full transition-all duration-700`}
                            style={{ width: `${item.share}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Benchmark Indicator */}
                  <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-3 text-xs text-[#172033] flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-[#2563EB]">Empirical Validation</div>
                      <div className="text-[11px] text-[#64748B]">120 Ground-Truth Jobs Evaluated</div>
                    </div>
                    <span className="font-mono text-sm font-bold text-[#14213D]">78.5% Correct</span>
                  </div>
                </div>

                {/* Floating Micro Card 1: Regional Focus */}
                <div className="absolute -bottom-6 -left-6 hidden sm:flex items-center gap-3 rounded-xl border border-[#E2E8F0] bg-white p-3.5 shadow-lg animate-bounce duration-1000">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-50 text-[#16A34A] border border-emerald-100">
                    <Globe className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-[#172033]">4 Regional Markets</div>
                    <div className="text-[10px] text-[#64748B]">Normalized Cross-Comparison</div>
                  </div>
                </div>

                {/* Floating Micro Card 2: Security & SSRF */}
                <div className="absolute -top-6 -right-6 hidden sm:flex items-center gap-3 rounded-xl border border-[#E2E8F0] bg-white p-3.5 shadow-lg">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-[#2563EB] border border-blue-100">
                    <ShieldCheck className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-[#172033]">SSRF Security Perimeter</div>
                    <div className="text-[10px] text-[#64748B]">Domain Whitelist Governance</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. About the Research – What Is This Platform? */}
      <section id="about" className="py-16 sm:py-24 bg-white border-y border-[#E2E8F0]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-12 lg:grid-cols-12 lg:items-center">
            {/* Left Narrative Column */}
            <div className="lg:col-span-7 space-y-6">
              <div className="inline-flex items-center gap-1.5 rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-[#2563EB]">
                <FileText className="h-3.5 w-3.5" />
                Research Foundation & Scope
              </div>

              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#14213D]">
                Understanding the IT Labour Market Through Data
              </h2>

              <div className="space-y-4 text-sm sm:text-base text-[#64748B] leading-relaxed">
                <p>
                  The IT industry is continuously evolving, with new technologies, tools, and technical skills becoming increasingly important. However, understanding which skills employers actually demand requires more than manually reviewing individual job advertisements.
                </p>
                <p>
                  This research introduces a quantitative framework that collects IT job advertisements from multiple online sources, processes and validates the extracted information, and transforms unstructured job descriptions into structured data for meaningful analysis.
                </p>
                <p>
                  By analyzing this information, the platform helps identify technical skill demand, compare regional labour-market patterns, understand role distributions, and explore compensation information where available.
                </p>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => scrollToSection('workflow')}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#2563EB] hover:underline"
                >
                  <span>Explore the six-stage research methodology</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {/* Right Structural Pillars Column */}
            <div className="lg:col-span-5 space-y-4">
              <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-5 space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 text-[#2563EB]">
                    <Layers className="h-4 w-4" />
                  </div>
                  <h3 className="text-sm font-bold text-[#172033]">Unstructured to Canonical Mapping</h3>
                </div>
                <p className="text-xs text-[#64748B] leading-relaxed pl-11">
                  Transforms messy, free-text vacancy descriptions into a normalized multi-tier taxonomy of programming languages, libraries, databases, and DevOps tools.
                </p>
              </div>

              <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-5 space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-[#16A34A]">
                    <Globe className="h-4 w-4" />
                  </div>
                  <h3 className="text-sm font-bold text-[#172033]">Cross-Portal Normalization</h3>
                </div>
                <p className="text-xs text-[#64748B] leading-relaxed pl-11">
                  Handles distinct portal layout variations across Sri Lanka, India, Singapore, and Malaysia to facilitate unbiased regional comparisons.
                </p>
              </div>

              <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-5 space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-100 text-[#2563EB]">
                    <ShieldCheck className="h-4 w-4" />
                  </div>
                  <h3 className="text-sm font-bold text-[#172033]">Empirical Ground-Truth Evaluation</h3>
                </div>
                <p className="text-xs text-[#64748B] leading-relaxed pl-11">
                  Quantifies extraction precision and completeness against human-annotated benchmark datasets with statistical confidence intervals.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Why Did We Develop This Platform? */}
      <section className="py-16 sm:py-24 bg-[#F8FAFC]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-12">
          {/* Section Header */}
          <div className="text-center max-w-3xl mx-auto space-y-3">
            <span className="inline-flex items-center rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-[#2563EB]">
              Problem Formulation
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#14213D]">
              Why This Research Matters
            </h2>
            <p className="text-sm text-[#64748B]">
              Addressing core computational challenges in web scraping, information extraction, and labour-market analytics.
            </p>
          </div>

          {/* 4 Problem Cards */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {/* Card 01 */}
            <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-2xs hover:shadow-xs transition-shadow space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-2xl font-extrabold text-blue-600/30">01</span>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-[#2563EB]">
                  <Globe className="h-5 w-5" />
                </div>
              </div>
              <h3 className="text-base font-bold text-[#172033]">
                Fragmented Job Market Information
              </h3>
              <p className="text-xs text-[#64748B] leading-relaxed">
                IT job advertisements are distributed across different recruitment websites and platforms, making it difficult to understand the overall demand for technical skills.
              </p>
            </div>

            {/* Card 02 */}
            <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-2xs hover:shadow-xs transition-shadow space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-2xl font-extrabold text-blue-600/30">02</span>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-50 text-sky-600">
                  <Code2 className="h-5 w-5" />
                </div>
              </div>
              <h3 className="text-base font-bold text-[#172033]">
                Unstructured Job Descriptions
              </h3>
              <p className="text-xs text-[#64748B] leading-relaxed">
                Job advertisements contain valuable technical information, but the information is presented in different formats and requires systematic processing.
              </p>
            </div>

            {/* Card 03 */}
            <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-2xs hover:shadow-xs transition-shadow space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-2xl font-extrabold text-blue-600/30">03</span>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                  <BarChart3 className="h-5 w-5" />
                </div>
              </div>
              <h3 className="text-base font-bold text-[#172033]">
                Limited Comparative Insights
              </h3>
              <p className="text-xs text-[#64748B] leading-relaxed">
                Raw job counts alone cannot provide reliable comparisons between markets with different sample sizes and data distributions.
              </p>
            </div>

            {/* Card 04 */}
            <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-2xs hover:shadow-xs transition-shadow space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-2xl font-extrabold text-blue-600/30">04</span>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-[#16A34A]">
                  <ShieldCheck className="h-5 w-5" />
                </div>
              </div>
              <h3 className="text-base font-bold text-[#172033]">
                Data Reliability Challenges
              </h3>
              <p className="text-xs text-[#64748B] leading-relaxed">
                Automatically collected information may contain missing values, extraction errors, duplicates, and inconsistencies that require validation.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. How Does the Platform Work? (Workflow) */}
      <section id="workflow" className="py-16 sm:py-24 bg-white border-y border-[#E2E8F0]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-12">
          {/* Section Header */}
          <div className="text-center max-w-3xl mx-auto space-y-3">
            <span className="inline-flex items-center rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-[#2563EB]">
              End-to-End Pipeline
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#14213D]">
              From Job Advertisements to Research Insights
            </h2>
            <p className="text-sm text-[#64748B]">
              A reproducible six-stage academic pipeline engineered for automated multi-site extraction.
            </p>
          </div>

          {/* Connected Workflow Grid */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {[
              {
                step: '01',
                title: 'Collect Job Advertisements',
                desc: 'Gather job vacancy information from multiple recruitment platforms with SSRF security and polite delay crawling.',
                icon: Briefcase,
                color: 'text-blue-600',
                bg: 'bg-blue-50',
              },
              {
                step: '02',
                title: 'Inspect Raw Data',
                desc: 'Review collected job advertisement records, source URLs, extraction confidence, and raw portal payloads.',
                icon: FileText,
                color: 'text-sky-600',
                bg: 'bg-sky-50',
              },
              {
                step: '03',
                title: 'Clean & Validate',
                desc: 'Process records, strip noisy formatting, handle inconsistencies, and isolate data-quality exclusions.',
                icon: Sparkles,
                color: 'text-amber-600',
                bg: 'bg-amber-50',
              },
              {
                step: '04',
                title: 'Extract Technical Skills',
                desc: 'Identify technical competencies and tools from job descriptions using canonical skill taxonomies.',
                icon: Cpu,
                color: 'text-purple-600',
                bg: 'bg-purple-50',
              },
              {
                step: '05',
                title: 'Build Master Dataset',
                desc: 'Organize approved and processed records into an immutable SQLite master research database.',
                icon: Database,
                color: 'text-indigo-600',
                bg: 'bg-indigo-50',
              },
              {
                step: '06',
                title: 'Analyze & Generate Insights',
                desc: 'Explore technical skill demand, role distributions, regional comparisons, and empirical validation metrics.',
                icon: TrendingUp,
                color: 'text-emerald-600',
                bg: 'bg-emerald-50',
              },
            ].map((st) => {
              const Icon = st.icon;
              return (
                <div
                  key={st.step}
                  className="relative rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-6 shadow-2xs hover:border-blue-200 hover:bg-white transition-all space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-[#64748B]">STEP {st.step}</span>
                    <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${st.bg} ${st.color}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                  </div>
                  <h3 className="text-base font-bold text-[#172033]">{st.title}</h3>
                  <p className="text-xs text-[#64748B] leading-relaxed">{st.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 6. Platform Capabilities */}
      <section id="features" className="py-16 sm:py-24 bg-[#F8FAFC]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-12">
          {/* Section Header */}
          <div className="text-center max-w-3xl mx-auto space-y-3">
            <span className="inline-flex items-center rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-[#2563EB]">
              Analytical Modules
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#14213D]">
              One Platform. Multiple Research Capabilities.
            </h2>
            <p className="text-sm text-[#64748B]">
              Integrated subsystems designed for end-to-end IT labour market analysis.
            </p>
          </div>

          {/* 9 Feature Cards Grid */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[
              {
                title: 'Data Collection',
                desc: 'Collect IT job advertisements from multiple online sources through the existing scraping and historical import workflows.',
                icon: Globe,
                path: '/pages/1_Collect_Data',
              },
              {
                title: 'Data Cleaning',
                desc: 'Process raw records and prepare structured job advertisement information for analysis.',
                icon: Sparkles,
                path: '/pages/3_Clean_Data',
              },
              {
                title: 'Technical Skill Extraction',
                desc: 'Identify technical skills and competencies mentioned in job descriptions using taxonomy matching.',
                icon: Cpu,
                path: '/pages/5_Extract_Skills',
              },
              {
                title: 'Data Quality & Validation',
                desc: 'Evaluate scraping accuracy, benchmark matching, extraction correctness, and data quality across 17 empirical snapshots.',
                icon: ShieldCheck,
                path: '/pages/10_Scraping_Validation',
              },
              {
                title: 'Regional Labour-Market Analysis',
                desc: 'Compare technical skill demand across Sri Lanka, India, Singapore, and Malaysia using normalized metrics.',
                icon: BarChart3,
                path: '/pages/12_Regional_Analysis',
              },
              {
                title: 'Role & Skill Analysis',
                desc: 'Explore relationships between job roles and technical skill requirements across industries.',
                icon: Users,
                path: '/dashboard',
              },
              {
                title: 'Temporal Analysis',
                desc: 'Explore available time-based changes in job advertisement and skill-demand information over time.',
                icon: Clock,
                path: '/dashboard',
              },
              {
                title: 'Salary & Compensation Analysis',
                desc: 'Explore salary disclosure and compensation information where currency and values are available.',
                icon: DollarSign,
                path: '/pages/12_Regional_Analysis',
              },
              {
                title: 'Research Audit & Monitoring',
                desc: 'Review failures, exclusions, discrepancies, and validation information across past collection runs.',
                icon: AlertOctagon,
                path: '/pages/7_Failure_Logs',
              },
            ].map((f) => {
              const Icon = f.icon;
              return (
                <div
                  key={f.title}
                  onClick={() => onNavigateToApp(f.path)}
                  className="group cursor-pointer rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-2xs hover:border-blue-200 hover:shadow-md transition-all space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-[#2563EB] group-hover:bg-[#2563EB] group-hover:text-white transition-colors">
                      <Icon className="h-5 w-5" />
                    </div>
                    <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-[#2563EB] group-hover:translate-x-0.5 transition-all" />
                  </div>
                  <h3 className="text-base font-bold text-[#172033] group-hover:text-[#2563EB] transition-colors">
                    {f.title}
                  </h3>
                  <p className="text-xs text-[#64748B] leading-relaxed">{f.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 7. Research Opportunities & Practical Value */}
      <section id="opportunities" className="py-16 sm:py-24 bg-white border-y border-[#E2E8F0]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-12">
          {/* Section Header */}
          <div className="text-center max-w-3xl mx-auto space-y-3">
            <span className="inline-flex items-center rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-[#2563EB]">
              Stakeholder Value
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#14213D]">
              Unlocking Insights and Opportunities in the IT Industry
            </h2>
            <p className="text-sm text-[#64748B]">
              Translating computational research outputs into actionable value for education, research, and workforce development.
            </p>
          </div>

          {/* Audience Selector Tabs */}
          <div className="flex flex-wrap justify-center gap-2">
            {[
              { id: 'students', label: 'Students & Job Seekers', icon: Users },
              { id: 'universities', label: 'Universities & Curriculum Planners', icon: GraduationCap },
              { id: 'researchers', label: 'Researchers & Analysts', icon: FileText },
              { id: 'industry', label: 'Industry & Workforce Planning', icon: Building2 },
            ].map((tab) => {
              const Icon = tab.icon;
              const isSelected = activeAudienceTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveAudienceTab(tab.id as any)}
                  className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-semibold transition-all ${
                    isSelected
                      ? 'bg-[#2563EB] text-white shadow-xs'
                      : 'border border-[#E2E8F0] bg-[#F8FAFC] text-[#64748B] hover:text-[#172033] hover:bg-white'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Active Audience Content Card */}
          <div className="mx-auto max-w-4xl rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-8 shadow-xs">
            {activeAudienceTab === 'students' && (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 text-[#2563EB]">
                    <Users className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-[#172033]">For Students & Job Seekers</h3>
                    <p className="text-xs text-[#64748B]">Targeted technical skills insights to guide career pathways</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 pt-2">
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> In-Demand Technical Skills
                    </div>
                    <p className="text-[11px] text-[#64748B]">Understand which technical skills actually appear in current IT job postings.</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Emerging Technologies
                    </div>
                    <p className="text-[11px] text-[#64748B]">Explore emerging toolsets and frameworks across software, data, and QA domains.</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Role-Specific Profiling
                    </div>
                    <p className="text-[11px] text-[#64748B]">Identify competency clusters specifically demanded for distinct engineering roles.</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Strategic Learning Decisions
                    </div>
                    <p className="text-[11px] text-[#64748B]">Make more informed learning, self-study, and career development investments.</p>
                  </div>
                </div>
              </div>
            )}

            {activeAudienceTab === 'universities' && (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-100 text-purple-600">
                    <GraduationCap className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-[#172033]">For Universities & Curriculum Planners</h3>
                    <p className="text-xs text-[#64748B]">Empirical data to bridge academic syllabi with market realities</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 pt-2">
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Industry Alignment
                    </div>
                    <p className="text-[11px] text-[#64748B]">Understand advertised technical requirements across regional hiring platforms.</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Skill Gap Identification
                    </div>
                    <p className="text-[11px] text-[#64748B]">Spot potential discrepancies between undergraduate coursework and employer expectations.</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Evidence-Based Syllabi
                    </div>
                    <p className="text-[11px] text-[#64748B]">Support curriculum revision committees with empirical statistical evidence.</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Regional Benchmarking
                    </div>
                    <p className="text-[11px] text-[#64748B]">Compare domestic graduate preparation with international tech hub expectations.</p>
                  </div>
                </div>
              </div>
            )}

            {activeAudienceTab === 'researchers' && (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-100 text-sky-600">
                    <FileText className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-[#172033]">For Researchers & Analysts</h3>
                    <p className="text-xs text-[#64748B]">A reproducible, benchmarked testbed for web intelligence research</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 pt-2">
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Structured Corpus
                    </div>
                    <p className="text-[11px] text-[#64748B]">Access clean, multi-field job advertisement datasets with rich provenance metadata.</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Skill Co-occurrence
                    </div>
                    <p className="text-[11px] text-[#64748B]">Investigate skill clustering, technology stack couplings, and requirement matrices.</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Cross-National Comparisons
                    </div>
                    <p className="text-[11px] text-[#64748B]">Evaluate labour market similarity using Cosine, Jaccard, and Spearman rank metrics.</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Benchmark Evaluation
                    </div>
                    <p className="text-[11px] text-[#64748B]">Inspect extraction accuracy across JSON-LD, site adapters, and fallback architectures.</p>
                  </div>
                </div>
              </div>
            )}

            {activeAudienceTab === 'industry' && (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-[#16A34A]">
                    <Building2 className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-[#172033]">For Industry & Workforce Planning</h3>
                    <p className="text-xs text-[#64748B]">Data-driven clarity for recruitment planning and capability building</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 pt-2">
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Competency Standards
                    </div>
                    <p className="text-[11px] text-[#64748B]">Understand how industry competitors define required engineering capabilities.</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Role Distributions
                    </div>
                    <p className="text-[11px] text-[#64748B]">Examine hiring proportions across Software, DevOps, QA, and Data Engineering roles.</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Compensation Exploration
                    </div>
                    <p className="text-[11px] text-[#64748B]">Analyze salary disclosure patterns and benchmark compensation ranges where stated.</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white p-4 shadow-2xs space-y-1">
                    <div className="font-semibold text-xs text-[#172033] flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[#16A34A]" /> Talent Pipeline Design
                    </div>
                    <p className="text-[11px] text-[#64748B]">Design structured internal upskilling and talent development roadmaps.</p>
                  </div>
                </div>
              </div>
            )}

            <div className="pt-2 text-center text-[11px] text-[#64748B]">
              <em>Note: Presented as potential research applications and analytical opportunities, not as recruitment or hiring agency services.</em>
            </div>
          </div>
        </div>
      </section>

      {/* 8. Regional Research Focus */}
      <section id="regional" className="py-16 sm:py-24 bg-[#F8FAFC]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-12">
          {/* Section Header */}
          <div className="text-center max-w-3xl mx-auto space-y-3">
            <span className="inline-flex items-center rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-[#2563EB]">
              Cross-National Analysis
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#14213D]">
              Understanding IT Skill Demand Across Regional Markets
            </h2>
            <p className="text-sm text-[#64748B]">
              The research compares technical skill demand across selected regional IT markets using normalized measures to make comparisons more meaningful when sample sizes differ.
            </p>
          </div>

          {/* 4 Country Cards Grid */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {/* Sri Lanka */}
            <div className="rounded-2xl border-2 border-blue-200 bg-white p-6 shadow-xs relative overflow-hidden space-y-3">
              <div className="absolute top-0 right-0 bg-[#2563EB] text-white px-3 py-1 rounded-bl-lg text-[10px] font-bold uppercase tracking-wider">
                Focal Market
              </div>
              <div className="text-3xl">🇱🇰</div>
              <h3 className="text-lg font-bold text-[#172033]">Sri Lanka</h3>
              <p className="text-xs text-[#64748B] leading-relaxed">
                Primary investigation market for analyzing local technical capabilities, domestic skill demand trends, and IT workforce capability.
              </p>
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-[#2563EB] font-semibold">
                <span>Baseline Ecosystem</span>
                <span>Focal Hub</span>
              </div>
            </div>

            {/* India */}
            <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-2xs space-y-3">
              <div className="text-3xl">🇮🇳</div>
              <h3 className="text-lg font-bold text-[#172033]">India</h3>
              <p className="text-xs text-[#64748B] leading-relaxed">
                Large-scale regional technology hub providing enterprise software, SaaS, and global outsourcing scale benchmarking.
              </p>
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-[#64748B]">
                <span>Comparator Market</span>
                <span>Scale Benchmark</span>
              </div>
            </div>

            {/* Singapore */}
            <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-2xs space-y-3">
              <div className="text-3xl">🇸🇬</div>
              <h3 className="text-lg font-bold text-[#172033]">Singapore</h3>
              <p className="text-xs text-[#64748B] leading-relaxed">
                Advanced APAC technology ecosystem representing high-density specialized roles in cloud architecture, AI, and fintech.
              </p>
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-[#64748B]">
                <span>Comparator Market</span>
                <span>Mature APAC Hub</span>
              </div>
            </div>

            {/* Malaysia */}
            <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-2xs space-y-3">
              <div className="text-3xl">🇲🇾</div>
              <h3 className="text-lg font-bold text-[#172033]">Malaysia</h3>
              <p className="text-xs text-[#64748B] leading-relaxed">
                Rapidly developing Southeast Asian digital services market providing regional economic parity comparisons.
              </p>
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-[#64748B]">
                <span>Comparator Market</span>
                <span>Regional Parity</span>
              </div>
            </div>
          </div>

          {/* Analytical Footnote */}
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-2xs text-center text-xs text-[#64748B] max-w-3xl mx-auto flex items-center justify-center gap-2">
            <ShieldCheck className="h-4 w-4 text-[#2563EB]" />
            <span>
              Comparative metrics strictly employ proportional alignment (Cosine), overlap (Jaccard), and monotonic rank correlation (Spearman) without fabricated rankings.
            </span>
          </div>
        </div>
      </section>

      {/* 9. Research Methodology & Reliability */}
      <section className="py-16 sm:py-24 bg-white border-y border-[#E2E8F0]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-12">
          {/* Section Header */}
          <div className="text-center max-w-3xl mx-auto space-y-3">
            <span className="inline-flex items-center rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-[#2563EB]">
              Academic Integrity
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#14213D]">
              Built Around Structured Data and Measurable Quality
            </h2>
            <p className="text-sm text-[#64748B]">
              Rigorous quantitative principles guiding data governance, empirical validation, and reproducibility.
            </p>
          </div>

          {/* 8 Principles Grid */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                title: 'Multi-Source Collection',
                desc: 'Crawling across diverse job boards to prevent portal-specific sampling bias.',
              },
              {
                title: 'Structured Processing',
                desc: 'Standardized schemas for job title, company, description, and source metadata.',
              },
              {
                title: 'Skill Identification',
                desc: 'Taxonomy-driven competency extraction across software engineering domains.',
              },
              {
                title: 'Benchmark Evaluation',
                desc: 'Quantitative accuracy assessment verified against 120 ground-truth reference jobs.',
              },
              {
                title: 'Field-Level Validation',
                desc: 'Granular evaluation of True Positives, False Positives, and False Negatives.',
              },
              {
                title: 'Normalized Comparisons',
                desc: 'Proportional metric adjustments to account for national sample volume variance.',
              },
              {
                title: 'Statistical Confidence',
                desc: 'Wilson score intervals and standard error bounds applied to empirical metrics.',
              },
              {
                title: 'Transparent Audit Logs',
                desc: 'Comprehensive tracking of scraping exceptions, SSRF exclusions, and discrepancy logs.',
              },
            ].map((item, idx) => (
              <div
                key={item.title}
                className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-4 shadow-2xs space-y-1.5"
              >
                <div className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 text-[10px] font-bold text-[#2563EB]">
                    {idx + 1}
                  </span>
                  <h4 className="text-xs font-bold text-[#172033]">{item.title}</h4>
                </div>
                <p className="text-[11px] text-[#64748B] pl-7 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 10. Call to Action Banner */}
      <section className="py-16 bg-[#14213D] text-white text-center">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 space-y-6">
          <span className="inline-flex items-center rounded-full bg-white/10 px-3.5 py-1 text-xs font-semibold text-blue-200 border border-white/20">
            Interactive Academic Environment
          </span>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight">
            Ready to Explore the Research Platform?
          </h2>
          <p className="mx-auto max-w-2xl text-sm sm:text-base text-slate-300 leading-relaxed">
            Access the analytics dashboard, inspect collected job advertisement datasets, review empirical validation metrics, and examine comparative regional findings.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <button
              onClick={() => onNavigateToApp('/dashboard')}
              className="inline-flex items-center gap-2 rounded-xl bg-[#2563EB] px-6 py-3.5 text-xs sm:text-sm font-semibold text-white shadow-lg hover:bg-[#1D4ED8] transition-all"
            >
              <span>Launch Research Console</span>
              <ArrowRight className="h-4 w-4" />
            </button>
            <button
              onClick={onNavigateToLogin}
              className="inline-flex items-center gap-2 rounded-xl border border-white/30 bg-white/10 px-6 py-3.5 text-xs sm:text-sm font-semibold text-white hover:bg-white/20 transition-all"
            >
              Sign In to Account
            </button>
          </div>
        </div>
      </section>

      {/* 11. Footer */}
      <footer className="border-t border-[#E2E8F0] bg-white py-12 text-xs text-[#64748B]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
            {/* Column 1: Identity */}
            <div className="md:col-span-2 space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#2563EB] text-white font-bold text-sm">
                  IT
                </div>
                <span className="font-bold text-sm tracking-wide text-[#172033]">
                  IT Job Advertisement Analytics Platform
                </span>
              </div>
              <p className="max-w-md text-xs leading-relaxed text-[#64748B]">
                Quantitative Analysis Framework for Technical Skill Identification in IT Sector Jobs. Developed as an undergraduate research project at the Sri Lanka Institute of Information Technology (SLIIT).
              </p>
              <div className="text-[11px] text-[#64748B] pt-1">
                Faculty of Computing • Project ID: J26-SE-355
              </div>
            </div>

            {/* Column 2: Navigation Links */}
            <div className="space-y-2">
              <div className="font-bold text-xs uppercase tracking-wider text-[#172033]">
                Platform Navigation
              </div>
              <ul className="space-y-1.5 text-xs">
                <li>
                  <button onClick={() => scrollToSection('home')} className="hover:text-[#2563EB]">
                    Home
                  </button>
                </li>
                <li>
                  <button onClick={() => scrollToSection('about')} className="hover:text-[#2563EB]">
                    About Research
                  </button>
                </li>
                <li>
                  <button onClick={() => scrollToSection('workflow')} className="hover:text-[#2563EB]">
                    How It Works
                  </button>
                </li>
                <li>
                  <button onClick={() => scrollToSection('features')} className="hover:text-[#2563EB]">
                    Platform Features
                  </button>
                </li>
                <li>
                  <button onClick={() => scrollToSection('regional')} className="hover:text-[#2563EB]">
                    Regional Markets
                  </button>
                </li>
              </ul>
            </div>

            {/* Column 3: Direct Access & Login */}
            <div className="space-y-2">
              <div className="font-bold text-xs uppercase tracking-wider text-[#172033]">
                Access & Demo
              </div>
              <ul className="space-y-1.5 text-xs">
                <li>
                  <button onClick={onNavigateToLogin} className="hover:text-[#2563EB] font-medium">
                    User & Admin Login
                  </button>
                </li>
                <li>
                  <button onClick={() => onNavigateToApp('/dashboard')} className="hover:text-[#2563EB]">
                    Research Dashboard
                  </button>
                </li>
                <li>
                  <button onClick={() => onNavigateToApp('/pages/10_Scraping_Validation')} className="hover:text-[#2563EB]">
                    Validation Scorecard
                  </button>
                </li>
                <li>
                  <button onClick={() => onNavigateToApp('/pages/12_Regional_Analysis')} className="hover:text-[#2563EB]">
                    Regional Analysis
                  </button>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-8 border-t border-[#E2E8F0] pt-6 flex flex-col sm:flex-row items-center justify-between text-[11px] gap-2">
            <div>
              © 2026 IT Job Analytics Research Project • Sri Lanka Institute of Information Technology (SLIIT). All rights reserved.
            </div>
            <div className="flex items-center gap-2 text-emerald-600 font-medium">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Research Prototype Active</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

