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
              content: (last.content || "") + `\n\nFehler: ${event.message}`,
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
            content: `Verbindung zum Agenten fehlgeschlagen: ${(e as Error).message}`,
          };
        }
        return next;
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {loading && messages[messages.length - 1]?.role === "assistant" && !messages[messages.length - 1].content && (
          <div className="ml-9 flex items-center gap-2 text-xs text-slate-400">
            <Loader2 className="h-3 w-3 animate-spin" />
            Assistent denkt nach...
          </div>
        )}
      </div>

      {messages.length <= 1 && !loading && (
        <div className="flex flex-wrap gap-1.5 px-3 pb-2">
          {QUICK_PROMPTS.map((p) => (
            <button
              key={p}
              onClick={() => send(p)}
              className="rounded border border-white/10 bg-white/[0.055] px-3 py-1 text-xs text-slate-300 transition hover:border-[#f2c94c]/40 hover:text-[#f2c94c]"
            >
              {p}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2 border-t border-white/10 bg-[#151619] p-3">
        <input
          className="h-10 flex-1 rounded border border-white/10 bg-[#202328] px-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-[#f2c94c]/70 disabled:bg-[#151619]"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send(input)}
          placeholder={loading ? "Assistent arbeitet..." : "Nachricht an Assistent..."}
          disabled={loading}
        />
        <button
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-[#f2c94c] text-[#171717] transition hover:bg-[#ffd866] disabled:bg-slate-700 disabled:text-slate-400"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end gap-2">
        <div className="max-w-[78%] rounded rounded-br-none bg-[#f2c94c] px-3 py-2 text-sm font-medium whitespace-pre-wrap text-[#171717]">
          {message.content}
        </div>
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-[#f2c94c]/15">
          <User className="h-4 w-4 text-[#f2c94c]" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded bg-white/10">
        <Bot className="h-4 w-4 text-slate-300" />
      </div>
      <div className="min-w-0 flex-1 space-y-2">
        {message.toolCalls?.map((tc, i) => <ToolCallCard key={i} call={tc} />)}
        {message.content && (
          <div className="max-w-[88%] rounded rounded-bl-none bg-[#202328] px-3 py-2 text-sm whitespace-pre-wrap text-slate-100">
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
    <div className="max-w-[88%] overflow-hidden rounded border border-white/10 bg-[#111214] text-xs">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-2.5 py-1.5 transition hover:bg-white/5"
      >
        {open ? <ChevronDown className="h-3 w-3 text-slate-500" /> : <ChevronRight className="h-3 w-3 text-slate-500" />}
        <Wrench className="h-3 w-3 text-[#f2c94c]" />
        <span className="font-mono font-medium text-slate-300">{call.name}</span>
        {call.status === "pending" && <Loader2 className="ml-auto h-3 w-3 animate-spin text-slate-400" />}
        {call.status === "done" && <span className="ml-auto text-emerald-300">ok</span>}
        {call.status === "error" && <AlertTriangle className="ml-auto h-3 w-3 text-red-400" />}
      </button>
      {open && (
        <div className="space-y-1.5 border-t border-white/10 px-2.5 py-2 font-mono">
          {hasInput && (
            <div>
              <span className="text-slate-500">Eingabe:</span>{" "}
              <span className="text-slate-300">{JSON.stringify(call.input)}</span>
            </div>
          )}
          {call.output !== undefined && (
            <div>
              <span className="text-slate-500">Ausgabe:</span>{" "}
              <span className="break-all text-slate-300">
                {call.output.length > 300 ? call.output.slice(0, 300) + "..." : call.output}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
