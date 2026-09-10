import React from 'react';
import { Shield, Bell, User, LogOut, Activity } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Navbar({ activeAlertsCount = 0 }) {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 bg-[#0c101b] border-b border-slate-800/80 px-6 flex items-center justify-between sticky top-0 z-30 shadow-md">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-cyan-400 via-sky-200 to-indigo-300 bg-clip-text text-transparent">
              CloudIntelliGuard
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 font-mono font-semibold">
              GNN v1.0
            </span>
          </div>
          <p className="text-[11px] text-slate-400">Proactive Cloud Security Intelligence</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/40 border border-emerald-800/40 text-emerald-400 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          API Connected (:8001)
        </div>

        {activeAlertsCount > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-950/50 border border-rose-800/50 text-rose-300 text-xs">
            <Bell className="w-3.5 h-3.5 text-rose-400" />
            <span className="font-semibold">{activeAlertsCount}</span> active alerts
          </div>
        )}

        <div className="flex items-center gap-3 pl-3 border-l border-slate-800">
          <div className="flex items-center gap-2 text-slate-300 text-sm">
            <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-cyan-400 font-semibold border border-slate-700">
              {user?.username?.[0]?.toUpperCase() || 'A'}
            </div>
            <span className="font-medium text-xs text-slate-300">{user?.username || 'Admin'}</span>
          </div>

          <button
            onClick={logout}
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 transition-colors"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
