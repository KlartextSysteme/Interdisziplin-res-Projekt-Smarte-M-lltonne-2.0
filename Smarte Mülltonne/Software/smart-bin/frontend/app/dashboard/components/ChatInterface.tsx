"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Bot, User, ChevronDown, ChevronRight, Wrench, Loader2, AlertTriangle } from "lucide-react";
import { streamChat } from "@/lib/api";
import type { ChatMessage, ToolCall } from "@/types";

const QUICK_PROMPTS = [
  "Welche Tonnen sind voll?",
  "Plane die heutige Abholung und starte den Truck",
  "Status-Übersicht bitte",
];

interface Props {
  onActionComplete?: () => void;
}

export default function ChatInterface({ onActionComplete }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hallo! Ich bin dein Planungsagent. Frag mich nach dem Flotten-Status, lass mich Routen planen oder Tonnen sperren.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(messageText: string) {
    if (!messageText.trim() || loading) return;
    setLoading(true);
    setInput("");

    const userMsg: ChatMessage = { role: "user", content: messageText };
    const history = messages.filter((m) => m.role === "user" || m.role === "assistant");
    setMessages((m) => [...m, userMsg, { role: "assistant", content: "", toolCalls: [] }]);

    try {
      let hadAction = false;
      await streamChat(messageText, [...history, userMsg], (event) => {
        setMessages((m) => {
          const next = [...m];
          const last = next[next.length - 1];
          if (last.role !== "assistant") return next;

          if (event.type === "token") {
            next[next.length - 1] = { ...last, content: last.content + event.content };
          } else if (event.type === "tool_call") {
            const tc: ToolCall = { name: event.tool, input: event.input, status: "pending" };
            next[next.length - 1] = { ...last, toolCalls: [...(last.toolCalls ?? []), tc] };
            if (["plan_route", "dispatch_truck", "lock_bin", "unlock_bin", "empty_bin_manual"].includes(event.tool)) {
              hadAction = true;
            }
          } else if (event.type === "tool_result") {
            const calls = [...(last.toolCalls ?? [])];
            // Find last pending call with matching name
            for (let i = calls.length - 1; i >= 0; i--) {
              if (calls[i].name === event.tool && calls[i].status === "pending") {
                calls[i] = { ...calls[i], output: event.output, status: "done" };
                break;
              }
            }
            next[next.length - 1] = { ...last, toolCalls: calls };
          } else if (event.type === "error") {
            next[next.length - 1] = {
              ...last,
              content: (last.content || "") + `\n\n⚠️ Fehler: ${event.message}`,
            };
          }
          return next;
        });
      });

      if (hadAction) onActionComplete?.();
    } catch (e) {
      setMessages((m) => {
        const next = [...m];
        const last = next[next.length - 1];
        if (last.role === "assistant") {
          next[next.length - 1] = {
            ...last,
            content: `⚠️ Verbindung zum Agenten fehlgeschlagen: ${(e as Error).message}`,
          };
        }
        return next;
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {loading && messages[messages.length - 1]?.role === "assistant" && !messages[messages.length - 1].content && (
          <div className="flex items-center gap-2 text-xs text-slate-500 ml-9">
            <Loader2 className="w-3 h-3 animate-spin" />
            Agent denkt nach...
          </div>
        )}
      </div>

      {/* Quick-Prompt Chips */}
      {messages.length <= 1 && !loading && (
        <div className="px-3 pb-2 flex flex-wrap gap-1.5">
          {QUICK_PROMPTS.map((p) => (
            <button
              key={p}
              onClick={() => send(p)}
              className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-full px-3 py-1 transition"
            >
              {p}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2 p-3 border-t border-slate-200 bg-white">
        <input
          className="flex-1 rounded-full border border-slate-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-slate-50"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send(input)}
          placeholder={loading ? "Agent arbeitet..." : "Nachricht an Agent..."}
          disabled={loading}
        />
        <button
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          className="rounded-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white w-10 h-10 flex items-center justify-center transition shrink-0"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex gap-2 justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-blue-600 text-white px-3 py-2 text-sm whitespace-pre-wrap">
          {message.content}
        </div>
        <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center shrink-0">
          <User className="w-4 h-4 text-slate-600" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2 items-start">
      <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center shrink-0 mt-0.5">
        <Bot className="w-4 h-4 text-blue-600" />
      </div>
      <div className="flex-1 space-y-2 min-w-0">
        {/* Tool cards appear before/between the response text */}
        {message.toolCalls?.map((tc, i) => <ToolCallCard key={i} call={tc} />)}
        {message.content && (
          <div className="max-w-[85%] rounded-2xl rounded-bl-sm bg-slate-100 text-slate-900 px-3 py-2 text-sm whitespace-pre-wrap">
            {message.content}
          </div>
        )}
      </div>
    </div>
  );
}

function ToolCallCard({ call }: { call: ToolCall }) {
  const [open, setOpen] = useState(false);
  const hasInput = Object.keys(call.input).length > 0;

  return (
    <div className="max-w-[85%] rounded-lg border border-slate-200 bg-slate-50 text-xs overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-2.5 py-1.5 hover:bg-slate-100 transition"
      >
        {open ? <ChevronDown className="w-3 h-3 text-slate-400" /> : <ChevronRight className="w-3 h-3 text-slate-400" />}
        <Wrench className="w-3 h-3 text-slate-500" />
        <span className="font-mono text-slate-700 font-medium">{call.name}</span>
        {call.status === "pending" && <Loader2 className="w-3 h-3 animate-spin text-slate-400 ml-auto" />}
        {call.status === "done" && <span className="text-emerald-600 ml-auto">✓</span>}
        {call.status === "error" && <AlertTriangle className="w-3 h-3 text-red-500 ml-auto" />}
      </button>
      {open && (
        <div className="border-t border-slate-200 px-2.5 py-2 space-y-1.5 font-mono">
          {hasInput && (
            <div>
              <span className="text-slate-500">input:</span>{" "}
              <span className="text-slate-700">{JSON.stringify(call.input)}</span>
            </div>
          )}
          {call.output !== undefined && (
            <div>
              <span className="text-slate-500">output:</span>{" "}
              <span className="text-slate-700 break-all">
                {call.output.length > 300 ? call.output.slice(0, 300) + "..." : call.output}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
