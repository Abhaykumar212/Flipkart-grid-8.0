import { useState } from 'react';
import { CreditCard, ChevronDown, ChevronUp } from 'lucide-react';
import { formatINR } from '../../lib/format';

interface EMIPlan {
  monthly: number;
  months: number;
}

interface EMICalculatorProps {
  sellingPrice: number;
  emi?: EMIPlan;
}

export function EMICalculator({ sellingPrice, emi }: EMICalculatorProps) {
  const [expanded, setExpanded] = useState(false);

  const defaultPlans = [
    { months: 3, monthly: Math.ceil(sellingPrice / 3) },
    { months: 6, monthly: Math.ceil(sellingPrice / 6) },
    { months: 12, monthly: Math.ceil(sellingPrice / 12) },
  ];

  const plansToShow = emi 
    ? [emi, ...defaultPlans.filter(p => p.months !== emi.months)] 
    : defaultPlans;

  const visiblePlans = expanded ? plansToShow : [plansToShow[0]];

  return (
    <div className="border border-fk-border rounded-[2px] p-4 bg-white mb-4">
      <div className="flex items-center gap-2 mb-3">
        <CreditCard className="w-5 h-5 text-fk-muted" />
        <h3 className="font-medium text-fk-ink text-fk-base">EMI Options</h3>
      </div>
      
      <div className="space-y-3">
        {visiblePlans.map((plan, idx) => (
          <div key={idx} className="flex items-center justify-between py-2 border-b border-fk-border border-opacity-50 last:border-0 last:pb-0">
            <div>
              <p className="text-fk-ink font-medium">
                {formatINR(plan.monthly)} <span className="text-fk-muted font-normal text-fk-sm">x {plan.months} months</span>
              </p>
            </div>
            <div className="bg-green-50 text-fk-green text-[10px] font-bold px-2 py-0.5 rounded-[2px] border border-green-200">
              No Cost
            </div>
          </div>
        ))}
      </div>

      <button 
        onClick={() => setExpanded(!expanded)}
        className="text-fk-blue text-fk-sm font-medium mt-3 flex items-center gap-1 hover:underline"
      >
        {expanded ? 'Hide EMI plans' : 'View all EMI plans'}
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
    </div>
  );
}
