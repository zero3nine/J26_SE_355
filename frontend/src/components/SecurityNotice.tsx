import React from 'react';
import { AlertTriangle } from 'lucide-react';

export const SecurityNotice: React.FC = () => {
  return (
    <div className="flex items-start gap-3.5 rounded-xl border border-amber-200/90 bg-[#FFFBEB] p-4 text-[#78350F] shadow-xs">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-[#D97706]">
        <AlertTriangle className="h-4 w-4" />
      </div>
      <div className="text-xs md:text-sm leading-relaxed">
        <strong className="font-semibold text-amber-950">Security Notice:</strong>{' '}
        Only submit publicly accessible and permitted job detail links. Local/private IP addresses are
        blocked, and unknown external hosts require administrator domain approval.
      </div>
    </div>
  );
};
