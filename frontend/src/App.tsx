import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { LandingPage } from './components/LandingPage';
import { LoginPage } from './components/LoginPage';
import { ResearchDashboard } from './components/ResearchDashboard';
import { CollectData, ScrapingStatusInfo } from './components/CollectData';
import { RawData } from './components/RawData';
import { CleanData } from './components/CleanData';
import { ScrapingValidation } from './components/ScrapingValidation';
import { RegionalAnalysis } from './components/RegionalAnalysis';
import { ExternalDomains } from './components/ExternalDomains';
import { FailureLogs } from './components/FailureLogs';
import { NavigationItem } from './types/dashboard';
import { ExternalLink, ArrowLeft, Layers } from 'lucide-react';

export const App: React.FC = () => {
  // Public Portal is at '/', Login at '/login', Console starts at '/dashboard'
  const [currentPath, setCurrentPath] = useState<string>('/');
  const [currentPage, setCurrentPage] = useState<NavigationItem | { name: string; path: string }>({
    name: 'Research Dashboard',
    path: '/dashboard',
  });
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [scrapingStatus, setScrapingStatus] = useState<ScrapingStatusInfo | null>(null);

  const handleNavigate = (item: NavigationItem | { name: string; path: string }) => {
    setCurrentPath(item.path);
    setCurrentPage(item);
  };

  const getStreamlitUrl = (path: string) => {
    // Streamlit runs locally on default port 8501
    const cleanPath = path.replace(/^\/pages\//, '').replace(/\.py$/, '');
    return `http://localhost:8501/${cleanPath}`;
  };

  // 1. Landing Page (Public Portal)
  if (currentPath === '/') {
    return (
      <>
        {/* Hidden persistent container keeps any ongoing background scraping active */}
        <div className="hidden" aria-hidden="true">
          <CollectData
            onNavigateToRawData={() => handleNavigate({ name: '2 Raw Data', path: '/pages/2_Raw_Data' })}
            onStatusChange={setScrapingStatus}
          />
        </div>

        <LandingPage
          onNavigateToLogin={() => setCurrentPath('/login')}
          onNavigateToApp={(targetPath) =>
            handleNavigate({
              name: 'Research Dashboard',
              path: targetPath || '/dashboard',
            })
          }
        />
      </>
    );
  }

  // 2. Dedicated Login Interface
  if (currentPath === '/login') {
    return (
      <>
        {/* Hidden persistent container keeps any ongoing background scraping active */}
        <div className="hidden" aria-hidden="true">
          <CollectData
            onNavigateToRawData={() => handleNavigate({ name: '2 Raw Data', path: '/pages/2_Raw_Data' })}
            onStatusChange={setScrapingStatus}
          />
        </div>

        <LoginPage
          onNavigateToHome={() => setCurrentPath('/')}
          onNavigateToApp={(targetPath) =>
            handleNavigate({
              name: 'Research Dashboard',
              path: targetPath || '/dashboard',
            })
          }
        />
      </>
    );
  }

  // 3. Research Application Console (Dashboard & Analytics Modules)
  return (
    <div className="flex min-h-screen bg-[#F8FAFC] text-[#172033]">
      {/* Left Sidebar */}
      <Sidebar
        currentPath={currentPath}
        onNavigate={handleNavigate}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        isScrapingActive={scrapingStatus?.active}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        <Header
          onToggleSidebar={() => setIsSidebarOpen(true)}
          scrapingStatus={scrapingStatus}
          onNavigateToCollect={() => handleNavigate({ name: '1 Collect Data', path: '/pages/1_Collect_Data' })}
          onNavigateToRawData={() => handleNavigate({ name: '2 Raw Data', path: '/pages/2_Raw_Data' })}
          onNavigateToHome={() => setCurrentPath('/')}
        />

        <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          {/* Always maintain CollectData mounted in DOM so background scraping processes, timers, logs, and form inputs persist across tab changes */}
          <div className={currentPath === '/pages/1_Collect_Data' ? 'block' : 'hidden'}>
            <CollectData
              onNavigateToRawData={() => handleNavigate({ name: '2 Raw Data', path: '/pages/2_Raw_Data' })}
              onStatusChange={setScrapingStatus}
            />
          </div>

          {currentPath === '/dashboard' && (
            <ResearchDashboard onNavigateToStreamlit={handleNavigate} />
          )}
          {currentPath === '/pages/2_Raw_Data' && (
            <RawData
              onNavigateToCollect={() => handleNavigate({ name: '1 Collect Data', path: '/pages/1_Collect_Data' })}
            />
          )}
          {currentPath === '/pages/3_Clean_Data' && (
            <CleanData
              onNavigateToCollect={() => handleNavigate({ name: '1 Collect Data', path: '/pages/1_Collect_Data' })}
              onNavigateToRaw={() => handleNavigate({ name: '2 Raw Data', path: '/pages/2_Raw_Data' })}
              onNavigateToExtract={() => handleNavigate({ name: '5 Extract Skills', path: '/pages/5_Extract_Skills' })}
            />
          )}
          {currentPath === '/pages/7_Failure_Logs' && (
            <FailureLogs />
          )}
          {currentPath === '/pages/8_External_Domains' && (
            <ExternalDomains />
          )}
          {currentPath === '/pages/10_Scraping_Validation' && (
            <ScrapingValidation />
          )}
          {currentPath === '/pages/12_Regional_Analysis' && (
            <RegionalAnalysis />
          )}
          {!['/dashboard', '/pages/1_Collect_Data', '/pages/2_Raw_Data', '/pages/3_Clean_Data', '/pages/7_Failure_Logs', '/pages/8_External_Domains', '/pages/10_Scraping_Validation', '/pages/12_Regional_Analysis'].includes(currentPath) && (
            <div className="mx-auto max-w-4xl space-y-6">
              <button
                onClick={() => handleNavigate({ name: 'Research Dashboard', path: '/dashboard' })}
                className="inline-flex items-center gap-2 rounded-lg border border-[#E2E8F0] bg-white px-3.5 py-2 text-xs font-medium text-[#172033] shadow-2xs hover:bg-slate-50 transition-colors"
              >
                <ArrowLeft className="h-4 w-4 text-[#64748B]" />
                Return to Research Dashboard
              </button>

              <div className="rounded-xl border border-[#E2E8F0] bg-white p-8 shadow-xs text-center space-y-4">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-[#2563EB] border border-blue-100">
                  <Layers className="h-7 w-7" />
                </div>

                <div className="space-y-1">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#64748B]">
                    Team Member Subsystem
                  </span>
                  <h2 className="text-2xl font-bold text-[#172033]">{currentPage.name}</h2>
                  <p className="mx-auto max-w-md text-sm text-[#64748B]">
                    This component is maintained within the Streamlit workspace to preserve team members'
                    existing data processing pipelines and workflows.
                  </p>
                </div>

                <div className="pt-2">
                  <a
                    href={getStreamlitUrl(currentPath)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-xl bg-[#2563EB] px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#1D4ED8] transition-colors"
                  >
                    Open Page in Streamlit (Port 8501)
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </div>

                <div className="pt-4 border-t border-[#E2E8F0] text-xs text-[#64748B] flex items-center justify-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                  Shared Backend Active • Safe Partial UI Migration Guarantee
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
