import React from 'react';
import { Info } from 'lucide-react';

export const InfoNotice: React.FC = () => {
  return (
    <div className="flex items-start gap-3.5 rounded-xl border border-blue-200/90 bg-[#EFF6FF] p-4 text-[#1E3A8A] shadow-xs">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-[#2563EB]">
        <Info className="h-4 w-4" />
      </div>
      <div className="flex flex-1 flex-col gap-1 text-xs md:text-sm leading-relaxed">
        <div>
          <strong className="font-semibold text-blue-950">Notice:</strong> Session data is temporary.
          Use the <strong>Master Dataset</strong> page to publish records to persistent storage once its
          database integration is configured.
        </div>
      </div>
    </div>
  );
};
