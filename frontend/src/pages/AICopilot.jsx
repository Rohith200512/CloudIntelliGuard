import React, { useState, useEffect, useRef } from 'react';
import { 
  Sparkles, 
  Send, 
  Bot, 
  User, 
  ShieldAlert, 
  ArrowRight, 
  Layers, 
  HelpCircle,
  Database,
  Terminal
} from 'lucide-react';
import { api } from '../api/client';

export default function AICopilot({ onNavigate, initialQuery }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Hello, Analyst. I am the CloudIntelliGuard AI Security Copilot. I have real-time visibility into monitored cloud identities, GNN anomaly scores, attack paths, and automated response enforcements. What would you like to investigate?',
      dataSources: ['live_telemetry', 'cloud_user_enforcements'],
      suggestedActions: [
        'Which user currently has the highest risk?',
        'Why was level6 flagged?',
        'Show the attack path for the latest incident.',
        'What automated actions were taken?',
      ],
    },
  ]);

  const [inputQuery, setInputQuery] = useState(initialQuery || '');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (queryText = inputQuery) => {
    const q = (queryText || '').trim();
    if (!q) return;

    const userMessage = { role: 'user', text: q };
    setMessages(prev => [...prev, userMessage]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await api.queryCopilot(q);
      const assistantMessage = {
        role: 'assistant',
        text: res.answer,
        intent: res.intent,
        dataSources: res.data_sources_used || [],
        suggestedActions: res.suggested_actions || [],
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Copilot query error:', err);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: 'Unable to query security telemetry. Please verify backend connectivity.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-400 uppercase tracking-widest font-mono mb-1">
            <Sparkles className="w-3.5 h-3.5" />
            Security Intelligence Assistant
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">AI Copilot</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Ask natural language questions grounded in live telemetry, behavioral deviations, and automated security actions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-950/60 border border-indigo-800 text-[11px] font-mono text-indigo-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Grounded in Active DB
          </span>
        </div>
      </div>

      {/* Preset SOC Query Chips */}
      <div className="flex flex-wrap gap-2">
        {[
          'Which user currently has the highest risk?',
          'Why was level6 flagged?',
          'Show the attack path for the latest incident.',
          'What automated actions were taken?',
          'Which incidents are critical?',
        ].map((preset, i) => (
          <button
            key={i}
            onClick={() => handleSend(preset)}
            className="px-3 py-1.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 hover:text-white transition-all font-mono text-[11px]"
          >
            {preset}
          </button>
        ))}
      </div>

      {/* Chat Messages Container */}
      <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl p-6 min-h-[480px] max-h-[600px] overflow-y-auto space-y-6 flex flex-col justify-between">
        <div className="space-y-6">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-3.5 ${
                msg.role === 'user' ? 'flex-row-reverse' : ''
              }`}
            >
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md'
                  : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md'
              }`}>
                {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Content */}
              <div className={`space-y-2 max-w-2xl ${
                msg.role === 'user' ? 'text-right' : ''
              }`}>
                <div className={`inline-block p-4 rounded-2xl text-xs leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-tr-none text-left'
                    : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none whitespace-pre-line'
                }`}>
                  {msg.text}
                </div>

                {/* Data Sources and Suggestions (Assistant Only) */}
                {msg.role === 'assistant' && (
                  <div className="space-y-2 pt-1">
                    {msg.dataSources && msg.dataSources.length > 0 && (
                      <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500">
                        <Database className="w-3 h-3 text-cyan-400" />
                        <span>Sources: {msg.dataSources.join(', ')}</span>
                      </div>
                    )}

                    {msg.suggestedActions && msg.suggestedActions.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {msg.suggestedActions.map((action, ai) => (
                          <button
                            key={ai}
                            onClick={() => handleSend(action)}
                            className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/60 text-[11px] text-cyan-300 font-mono"
                          >
                            ➔ {action}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-3 text-xs text-indigo-400 font-mono">
              <Bot className="w-5 h-5 animate-pulse" />
              <span>Querying live security telemetry & correlating graph paths...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Box */}
      <div className="relative">
        <textarea
          rows={2}
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question (e.g. Why was level6 blocked? What are the critical incidents?)..."
          className="w-full p-4 pr-24 rounded-2xl bg-[#090e1a] border border-slate-700/90 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 shadow-xl resize-none font-sans"
        />

        <button
          onClick={() => handleSend()}
          disabled={loading || !inputQuery.trim()}
          className="absolute right-3.5 bottom-3.5 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-40 text-white text-xs font-semibold shadow-md flex items-center gap-1.5"
        >
          <span>Ask</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
