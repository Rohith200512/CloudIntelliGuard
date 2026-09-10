import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon, color = 'cyan', trend }) {
  const colorMap = {
    cyan: 'from-cyan-500/10 to-blue-500/5 text-cyan-400 border-cyan-500/20 shadow-cyan-500/5',
    emerald: 'from-emerald-500/10 to-green-500/5 text-emerald-400 border-emerald-500/20 shadow-emerald-500/5',
    rose: 'from-rose-500/10 to-red-500/5 text-rose-400 border-rose-500/20 shadow-rose-500/5',
    amber: 'from-amber-500/10 to-yellow-500/5 text-amber-400 border-amber-500/20 shadow-amber-500/5',
    indigo: 'from-indigo-500/10 to-purple-500/5 text-indigo-400 border-indigo-500/20 shadow-indigo-500/5',
  };

  const iconBgMap = {
    cyan: 'bg-cyan-950/60 border-cyan-800/60 text-cyan-400',
    emerald: 'bg-emerald-950/60 border-emerald-800/60 text-emerald-400',
    rose: 'bg-rose-950/60 border-rose-800/60 text-rose-400',
    amber: 'bg-amber-950/60 border-amber-800/60 text-amber-400',
    indigo: 'bg-indigo-950/60 border-indigo-800/60 text-indigo-400',
  };

  return (
    <div className={`p-5 rounded-2xl bg-gradient-to-br ${colorMap[color]} border backdrop-blur-sm relative overflow-hidden transition-all hover:scale-[1.01]`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 mb-1 tracking-wide uppercase">{title}</p>
          <h3 className="text-2xl font-bold text-white font-mono tracking-tight">{value}</h3>
        </div>
        {Icon && (
          <div className={`w-11 h-11 rounded-xl border flex items-center justify-center ${iconBgMap[color]}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
      {subtitle && (
        <p className="text-xs text-slate-400 mt-2 flex items-center gap-1.5">
          {trend && (
            <span className={trend > 0 ? 'text-rose-400 font-semibold' : 'text-emerald-400 font-semibold'}>
              {trend > 0 ? `+${trend}` : trend}
            </span>
          )}
          <span>{subtitle}</span>
        </p>
      )}
    </div>
  );
}
