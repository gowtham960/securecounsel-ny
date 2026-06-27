"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE_URL = "http://localhost:8000";

type DemoUser = {
  user_email: string;
  display_name: string;
  role: string;
  allowed_matter_ids: string[];
};

type Matter = {
  matter_id: string;
  matter_name: string;
  client_name: string;
  matter_type: string;
  status: string;
  description: string;
  primary_document: string;
};

type Citation = {
  collection: string;
  document_id: string;
  chunk_id: string;
  citation: string;
  score: number;
};

type AgentPlan = {
  task_type: string;
  sources_needed: string[];
  reason: string;
  steps: string[];
};

type SecurityMetadata = {
  injection_label: string;
  input_pii_detected: boolean;
  output_pii_detected: boolean;
  relevance_score: number | null;
  evidence_status: string | null;
  faithfulness_score: number | null;
  hallucination_status: string | null;
  final_status: string;
};

type ChatResponse = {
  answer: string;
  citations: Citation[];
  agent_plan: AgentPlan | null;
  security: SecurityMetadata;
  request_id: string;
  debug: Record<string, unknown>;
};

const DEMO_USERS: DemoUser[] = [
  {
    user_email: "attorney@demo-law.com",
    display_name: "Ava Johnson",
    role: "Attorney",
    allowed_matter_ids: ["matter_acme_smith", "matter_omega_contract"],
  },
  {
    user_email: "paralegal@demo-law.com",
    display_name: "Ben Carter",
    role: "Paralegal",
    allowed_matter_ids: ["matter_acme_smith"],
  },
  {
    user_email: "admin@demo-law.com",
    display_name: "Maria Lopez",
    role: "Firm Admin",
    allowed_matter_ids: ["*"],
  },
];

const SEARCH_SCOPES = [
  {
    value: "current_matter",
    label: "Current Matter Only",
  },
  {
    value: "firm_knowledge_base",
    label: "Firm Knowledge Base",
  },
  {
    value: "ny_legal_authorities",
    label: "NY Legal Authorities",
  },
  {
    value: "all_authorized_sources",
    label: "All Authorized Sources",
  },
];

function Pill({
  label,
  value,
}: {
  label: string;
  value: string | number | boolean | null;
}) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/70 px-3 py-2">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-100">
        {value === null ? "N/A" : String(value)}
      </p>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl">
      <h2 className="mb-4 text-lg font-semibold text-white">{title}</h2>
      {children}
    </section>
  );
}

export default function Home() {
  const [selectedUserEmail, setSelectedUserEmail] = useState(
    "attorney@demo-law.com"
  );
  const [matters, setMatters] = useState<Matter[]>([]);
  const [selectedMatter, setSelectedMatter] = useState<Matter | null>(null);
  const [question, setQuestion] = useState(
    "What does the agreement say about non-solicitation?"
  );
  const [searchScope, setSearchScope] = useState("current_matter");
  const [chatResponse, setChatResponse] = useState<ChatResponse | null>(null);
  const [isLoadingMatters, setIsLoadingMatters] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedUser = useMemo(() => {
    return (
      DEMO_USERS.find((user) => user.user_email === selectedUserEmail) ??
      DEMO_USERS[0]
    );
  }, [selectedUserEmail]);

  async function loadMatters(userEmail: string) {
    setIsLoadingMatters(true);
    setError(null);
    setSelectedMatter(null);
    setChatResponse(null);

    try {
      const response = await fetch(`${API_BASE_URL}/matters`, {
        headers: {
          "x-demo-user": userEmail,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to load matters. Status ${response.status}`);
      }

      const data = await response.json();
      setMatters(data.items ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load matters.");
    } finally {
      setIsLoadingMatters(false);
    }
  }

  useEffect(() => {
    loadMatters(selectedUserEmail);
  }, [selectedUserEmail]);

  async function askQuestion() {
    if (!selectedMatter) {
      setError("Select a matter first.");
      return;
    }

    setIsAsking(true);
    setError(null);
    setChatResponse(null);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-demo-user": selectedUserEmail,
        },
        body: JSON.stringify({
          query: question,
          matter_id: selectedMatter.matter_id,
          search_scope: searchScope,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? `Request failed. Status ${response.status}`);
      }

      setChatResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to ask question.");
    } finally {
      setIsAsking(false);
    }
  }

  function backToMatters() {
    setSelectedMatter(null);
    setChatResponse(null);
    setError(null);
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-6 shadow-2xl">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-400">
            SecureCounsel NY
          </p>
          <h1 className="mt-3 text-3xl font-bold text-white md:text-5xl">
            Matter Intelligence Workspace
          </h1>
          <p className="mt-4 max-w-3xl text-slate-300">
            Select a demo user, choose an assigned matter, and work inside a
            secure legal AI workspace with role-based access, citations,
            security checks, and audit-ready responses.
          </p>
        </header>

        <Section title="Demo Login">
          <div className="grid gap-4 md:grid-cols-3">
            {DEMO_USERS.map((user) => {
              const isSelected = user.user_email === selectedUserEmail;

              return (
                <button
                  key={user.user_email}
                  onClick={() => setSelectedUserEmail(user.user_email)}
                  className={`rounded-2xl border p-4 text-left transition ${
                    isSelected
                      ? "border-cyan-400 bg-cyan-950/40"
                      : "border-slate-800 bg-slate-900 hover:border-slate-600"
                  }`}
                >
                  <p className="text-lg font-semibold text-white">
                    {user.display_name}
                  </p>
                  <p className="mt-1 text-sm text-cyan-300">{user.role}</p>
                  <p className="mt-3 text-xs text-slate-400">
                    {user.user_email}
                  </p>
                </button>
              );
            })}
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <Pill label="Current User" value={selectedUser.display_name} />
            <Pill label="Role" value={selectedUser.role} />
            <Pill
              label="Demo Auth Header"
              value={`x-demo-user: ${selectedUser.user_email}`}
            />
          </div>
        </Section>

        {error && (
          <div className="mt-6 rounded-2xl border border-red-800 bg-red-950/40 p-4 text-red-200">
            {error}
          </div>
        )}

        {!selectedMatter && (
          <div className="mt-6">
            <Section title="Assigned Matters">
              {isLoadingMatters ? (
                <p className="text-slate-400">Loading assigned matters...</p>
              ) : matters.length === 0 ? (
                <p className="text-slate-400">
                  No matters assigned to this user.
                </p>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {matters.map((matter) => (
                    <button
                      key={matter.matter_id}
                      onClick={() => setSelectedMatter(matter)}
                      className="rounded-2xl border border-slate-800 bg-slate-900 p-5 text-left transition hover:border-cyan-400 hover:bg-slate-900/70"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-lg font-semibold text-white">
                            {matter.matter_name}
                          </p>
                          <p className="mt-1 text-sm text-cyan-300">
                            {matter.client_name}
                          </p>
                        </div>
                        <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">
                          {matter.status}
                        </span>
                      </div>

                      <p className="mt-4 text-sm text-slate-300">
                        {matter.description}
                      </p>

                      <div className="mt-4 space-y-1 text-xs text-slate-500">
                        <p>Type: {matter.matter_type}</p>
                        <p>Primary document: {matter.primary_document}</p>
                      </div>

                      <p className="mt-5 text-sm font-semibold text-cyan-300">
                        Open workspace →
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </Section>
          </div>
        )}

        {selectedMatter && (
          <div className="mt-6 grid gap-6 xl:grid-cols-[420px_1fr]">
            <div className="space-y-6">
              <Section title="Selected Matter">
                <button
                  onClick={backToMatters}
                  className="mb-4 rounded-xl border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-cyan-400 hover:text-cyan-300"
                >
                  ← Back to assigned matters
                </button>

                <h2 className="text-2xl font-bold text-white">
                  {selectedMatter.matter_name}
                </h2>
                <p className="mt-2 text-cyan-300">
                  {selectedMatter.client_name}
                </p>
                <p className="mt-4 text-sm text-slate-300">
                  {selectedMatter.description}
                </p>

                <div className="mt-5 grid gap-3">
                  <Pill label="Matter ID" value={selectedMatter.matter_id} />
                  <Pill label="Matter Type" value={selectedMatter.matter_type} />
                  <Pill
                    label="Primary Document"
                    value={selectedMatter.primary_document}
                  />
                </div>
              </Section>

              <Section title="Workspace Tools">
                <div className="grid gap-3">
                  <button className="rounded-xl border border-cyan-700 bg-cyan-950/40 px-4 py-3 text-left text-sm font-semibold text-cyan-200">
                    Matter Chat
                  </button>
                  <button className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-left text-sm text-slate-400" disabled>
                    Draft from Matter Context — coming next
                  </button>
                  <button className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-left text-sm text-slate-400" disabled>
                    Document Upload — coming soon
                  </button>
                  <button className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-left text-sm text-slate-400" disabled>
                    Key Dates — coming soon
                  </button>
                </div>
              </Section>
            </div>

            <div className="space-y-6">
              <Section title="Matter Chat">
                <label className="block text-sm font-medium text-slate-300">
                  Question
                </label>
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  className="mt-2 min-h-28 w-full rounded-2xl border border-slate-700 bg-slate-900 p-4 text-sm text-white outline-none focus:border-cyan-400"
                />

                <label className="mt-5 block text-sm font-medium text-slate-300">
                  Search Scope
                </label>
                <select
                  value={searchScope}
                  onChange={(event) => setSearchScope(event.target.value)}
                  className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-900 p-3 text-sm text-white outline-none focus:border-cyan-400"
                >
                  {SEARCH_SCOPES.map((scope) => (
                    <option key={scope.value} value={scope.value}>
                      {scope.label}
                    </option>
                  ))}
                </select>

                <button
                  onClick={askQuestion}
                  disabled={isAsking}
                  className="mt-5 w-full rounded-2xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isAsking ? "Asking SecureCounsel..." : "Ask SecureCounsel"}
                </button>
              </Section>

              {chatResponse && (
                <>
                  <Section title="Answer">
                    <pre className="whitespace-pre-wrap rounded-2xl bg-slate-900 p-4 text-sm leading-7 text-slate-100">
                      {chatResponse.answer}
                    </pre>
                  </Section>

                  <Section title="Security">
                    <div className="grid gap-3 md:grid-cols-3">
                      <Pill
                        label="Final Status"
                        value={chatResponse.security.final_status}
                      />
                      <Pill
                        label="Injection"
                        value={chatResponse.security.injection_label}
                      />
                      <Pill
                        label="Evidence"
                        value={chatResponse.security.evidence_status}
                      />
                      <Pill
                        label="Faithfulness"
                        value={chatResponse.security.hallucination_status}
                      />
                      <Pill
                        label="Top Score"
                        value={chatResponse.security.relevance_score}
                      />
                      <Pill
                        label="Request ID"
                        value={chatResponse.request_id}
                      />
                    </div>
                  </Section>

                  <Section title="Citations">
                    {chatResponse.citations.length === 0 ? (
                      <p className="text-slate-400">No citations returned.</p>
                    ) : (
                      <div className="space-y-3">
                        {chatResponse.citations.map((citation) => (
                          <div
                            key={`${citation.document_id}-${citation.chunk_id}`}
                            className="rounded-2xl border border-slate-800 bg-slate-900 p-4"
                          >
                            <p className="font-semibold text-white">
                              {citation.citation}
                            </p>
                            <p className="mt-2 text-sm text-slate-400">
                              {citation.collection} · {citation.document_id}
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              {citation.chunk_id}
                            </p>
                            <p className="mt-2 text-sm text-cyan-300">
                              Score: {citation.score}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </Section>

                  {chatResponse.agent_plan && (
                    <Section title="Agent Plan">
                      <p className="text-sm text-slate-300">
                        <span className="font-semibold text-white">
                          Task:
                        </span>{" "}
                        {chatResponse.agent_plan.task_type}
                      </p>
                      <p className="mt-2 text-sm text-slate-300">
                        <span className="font-semibold text-white">
                          Sources:
                        </span>{" "}
                        {chatResponse.agent_plan.sources_needed.join(", ")}
                      </p>
                      <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-slate-300">
                        {chatResponse.agent_plan.steps.map((step) => (
                          <li key={step}>{step}</li>
                        ))}
                      </ol>
                    </Section>
                  )}

                  <Section title="Retrieval Debug">
                    <pre className="max-h-96 overflow-auto rounded-2xl bg-slate-900 p-4 text-xs text-slate-300">
                      {JSON.stringify(chatResponse.debug, null, 2)}
                    </pre>
                  </Section>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}